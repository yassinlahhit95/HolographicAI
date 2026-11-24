#include "HoloDirector.h"
#include "HoloStateSubsystem.h"
#include "Audio.h"
#include "Camera/CameraActor.h"
#include "EngineUtils.h"
#include "GameFramework/GameUserSettings.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Common/UdpSocketBuilder.h"
#include "Components/AudioComponent.h"
#include "Components/InputComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "HAL/IConsoleManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Sound/SoundWaveProcedural.h"

DEFINE_LOG_CATEGORY_STATIC(LogHoloDirector, Log, All);

namespace
{
	constexpr float FrameSec = 0.01f;   // un valor de boca cada 10 ms
	constexpr float WindowSec = 0.025f; // ventana de analisis
	constexpr uint64 StatusKey = 0x484F4C4F;   // clave fija del mensaje en pantalla
	constexpr uint64 CameraKey = 0x484F4C50;   // Etapa 4: linea del estado de la camara

	FString EscapeJson(const FString& S)
	{
		FString Out = S;
		Out.ReplaceInline(TEXT("\\"), TEXT("\\\\"));
		Out.ReplaceInline(TEXT("\""), TEXT("\\\""));
		return Out;
	}
}

AHoloDirector::AHoloDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;   // antes de que se actualice la animacion
}

// ================================================================ audio
bool AHoloDirector::LoadClip(const FString& InPath, FHoloClip& Out)
{
	// Ruta relativa = carpeta Voice del proyecto; absoluta = tal cual (respuestas de Python).
	const FString Path = FPaths::IsRelative(InPath)
		? FPaths::Combine(FPaths::ProjectDir(), TEXT("Voice"), InPath) : InPath;
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *Path))
	{
		UE_LOG(LogHoloDirector, Error, TEXT("No encuentro el audio: %s"), *Path);
		return false;
	}
	FWaveModInfo Info;
	FString Err;
	if (!Info.ReadWaveInfo(Bytes.GetData(), Bytes.Num(), &Err))
	{
		UE_LOG(LogHoloDirector, Error, TEXT("WAV no valido %s: %s"), *Path, *Err);
		return false;
	}
	if (*Info.pBitsPerSample != 16)
	{
		UE_LOG(LogHoloDirector, Error, TEXT("%s: solo se admite PCM de 16 bits"), *Path);
		return false;
	}
	Out.Name = FPaths::GetCleanFilename(Path);
	Out.SampleRate = *Info.pSamplesPerSec;
	Out.NumChannels = *Info.pChannels;
	Out.Pcm.Reset();
	Out.Pcm.Append(Info.SampleDataStart, Info.SampleDataSize);
	const int32 Frames = Info.SampleDataSize / (2 * Out.NumChannels);
	Out.Duration = float(Frames) / float(Out.SampleRate);
	AnalyzeClip(Out);
	UE_LOG(LogHoloDirector, Log, TEXT("Audio cargado: %s (%.1f s, %d Hz)"), *Out.Name, Out.Duration, Out.SampleRate);
	return true;
}

// Analiza el audio: volumen (apertura de la boca) y "brillo" del sonido
// (cruces por cero: alto en s/f/z = boca ancha; bajo y fuerte = boca redonda).
void AHoloDirector::AnalyzeClip(FHoloClip& Clip)
{
	const int16* S = reinterpret_cast<const int16*>(Clip.Pcm.GetData());
	const int32 Ch = Clip.NumChannels;
	const int32 Frames = Clip.Pcm.Num() / (2 * Ch);
	const int32 Hop = FMath::Max(1, int32(Clip.SampleRate * FrameSec));
	const int32 Win = FMath::Max(1, int32(Clip.SampleRate * WindowSec));
	// Los cruces por cero dependen de la frecuencia de muestreo: se normalizan a 22050 Hz.
	const float RateScale = Clip.SampleRate / 22050.f;

	TArray<float> Rms, Zcr;
	for (int32 Start = 0; Start < Frames; Start += Hop)
	{
		double Sum = 0.0;
		int32 Crossings = 0, N = 0;
		float Prev = 0.f;
		for (int32 i = FMath::Max(0, Start - Win / 2); i < FMath::Min(Frames, Start + Win / 2); ++i)
		{
			const float V = S[i * Ch] / 32768.f;   // primer canal
			Sum += V * V;
			if ((V >= 0.f) != (Prev >= 0.f)) ++Crossings;
			Prev = V;
			++N;
		}
		Rms.Add(N ? FMath::Sqrt(float(Sum / N)) : 0.f);
		Zcr.Add(N ? RateScale * float(Crossings) / N : 0.f);
	}

	// Normaliza con el percentil 95 para que cualquier voz/volumen de valores parecidos.
	TArray<float> Sorted = Rms;
	Sorted.Sort();
	const float P95 = FMath::Max(1e-4f, Sorted.Num() ? Sorted[int32(Sorted.Num() * 0.95f)] : 1.f);

	Clip.Open.SetNum(Rms.Num());
	Clip.Wide.SetNum(Rms.Num());
	Clip.Round.SetNum(Rms.Num());
	for (int32 i = 0; i < Rms.Num(); ++i)
	{
		const float E = FMath::Clamp(Rms[i] / P95, 0.f, 1.2f);
		const float Open = FMath::SmoothStep(0.06f, 0.85f, E);
		const float Fric = FMath::Clamp((Zcr[i] - 0.14f) / 0.16f, 0.f, 1.f);   // s, f, z, ch
		const float Dark = FMath::Clamp((0.07f - Zcr[i]) / 0.04f, 0.f, 1.f);   // o, u (sonido grave)
		Clip.Open[i] = Open * (1.f - 0.55f * Fric);
		Clip.Wide[i] = FMath::Max(Open, 0.3f * E) * Fric;
		Clip.Round[i] = Open * Dark;
	}
}

void AHoloDirector::StartClip(const FHoloClip& C)
{
	// Un sonido procedural nuevo por reproduccion (el anterior ya se consumio).
	Wave = NewObject<USoundWaveProcedural>(this);
	Wave->SetSampleRate(C.SampleRate);
	Wave->NumChannels = C.NumChannels;
	Wave->Duration = C.Duration;
	Wave->SoundGroup = SOUNDGROUP_Voice;
	Wave->bLooping = false;
	Wave->QueueAudio(C.Pcm.GetData(), C.Pcm.Num());

	if (Audio)
	{
		Audio->Stop();
		Audio->DestroyComponent();
	}
	Audio = UGameplayStatics::CreateSound2D(this, Wave, Volume, 1.f, 0.f, nullptr, false, false);
	if (!Audio)
	{
		UE_LOG(LogHoloDirector, Error, TEXT("No se pudo crear el audio (dispositivo de sonido?)"));
		return;
	}
	Audio->Play();
	Active = C;
	bActive = true;
	ClipStart = FPlatformTime::Seconds();
	UE_LOG(LogHoloDirector, Log, TEXT("Hablando: %s"), *C.Name);
	SendEvent(TEXT("speech_start"), FString::Printf(TEXT("\"file\":\"%s\",\"duration\":%.2f"), *EscapeJson(C.Name), C.Duration));
}

void AHoloDirector::StopAll()
{
	if (Audio)
	{
		Audio->Stop();
	}
	Queue.Reset();
	bActive = false;
	NextClipAt = -1.0;
	SetMouth(0.f, 0.f, 0.f);
}

void AHoloDirector::SetMouth(float Open, float Wide, float Round)
{
	if (UHoloStateSubsystem* St = GetWorld()->GetSubsystem<UHoloStateSubsystem>())
	{
		St->MouthOpen = Open;
		St->MouthWide = Wide;
		St->MouthRound = Round;
	}
}

void AHoloDirector::SetMode(uint8 NewMode)
{
	if (UHoloStateSubsystem* St = GetWorld()->GetSubsystem<UHoloStateSubsystem>())
	{
		St->Mode = static_cast<EHoloMode>(NewMode);
	}
	// Mientras piensa (o mientras Python genera voz, aunque ya este hablando la frase anterior)
	// la GPU la usa Chatterbox: Unreal le deja sitio.
	LastMode = NewMode;
	ApplyFpsLimit((NewMode == uint8(EHoloMode::Thinking) || bGpuBusy) ? ThinkingMaxFps : MaxFps);
}

void AHoloDirector::ApplyFpsLimit(int32 Fps)
{
	if (IConsoleVariable* CVar = IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS")))
	{
		CVar->Set(float(Fps), ECVF_SetByCode);
	}
}

// ================================================================ ciclo de vida
void AHoloDirector::BeginPlay()
{
	Super::BeginPlay();

	IntroClips.Reset();
	for (const FString& F : IntroFiles)
	{
		FHoloClip C;
		if (LoadClip(F, C))
		{
			C.GapBefore = IntroClips.Num() == 0 ? 0.f : GapBetweenClips;
			IntroClips.Add(MoveTemp(C));
		}
	}

	// Tecla R = repetir la presentacion (para pruebas).
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		EnableInput(PC);
		if (InputComponent)
		{
			InputComponent->BindKey(EKeys::R, IE_Pressed, this, &AHoloDirector::ReplayIntro);
			// Etapa 5: pantalla completa y vista con el raton
			InputComponent->BindKey(EKeys::F11, IE_Pressed, this, &AHoloDirector::ToggleFullscreen);
			InputComponent->BindKey(EKeys::LeftMouseButton, IE_DoubleClick, this, &AHoloDirector::ToggleFullscreen);
			InputComponent->BindKey(EKeys::MiddleMouseButton, IE_Pressed, this, &AHoloDirector::ResetView);
			InputComponent->BindKey(EKeys::C, IE_Pressed, this, &AHoloDirector::ResetView);
			InputComponent->BindKey(EKeys::MouseScrollUp, IE_Pressed, this, &AHoloDirector::ZoomIn);
			InputComponent->BindKey(EKeys::MouseScrollDown, IE_Pressed, this, &AHoloDirector::ZoomOut);
			InputComponent->BindKey(EKeys::H, IE_Pressed, this, &AHoloDirector::ToggleStatusText);
		}
		PC->bShowMouseCursor = true;
		FInputModeGameAndUI Mode;
		Mode.SetHideCursorDuringCapture(false);
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		PC->SetInputMode(Mode);
	}
	SetupMouseView();
	if (FParse::Param(FCommandLine::Get(), TEXT("holofull")))
	{
		ToggleFullscreen();
	}

	ApplyFpsLimit(MaxFps);
	OpenSockets();
	SendEvent(TEXT("ready"));

	if (IntroClips.Num() > 0)
	{
		Queue = IntroClips;
		bPlayingIntro = true;
		NextClipAt = FPlatformTime::Seconds() + StartDelay;
		SetMode(uint8(EHoloMode::Greeting));   // mira al frente y sonrie ya antes de hablar
	}
	else
	{
		bIntroDone = true;
	}
}

void AHoloDirector::EndPlay(const EEndPlayReason::Type Reason)
{
	StopAll();
	CloseSockets();
	if (GEngine)
	{
		GEngine->RemoveOnScreenDebugMessage(StatusKey);
		GEngine->RemoveOnScreenDebugMessage(CameraKey);
	}
	Super::EndPlay(Reason);
}

void AHoloDirector::ReplayIntro()
{
	if (IntroClips.Num() == 0) return;
	UE_LOG(LogHoloDirector, Log, TEXT("Repetir presentacion"));
	StopAll();
	Queue = IntroClips;
	Queue[0].GapBefore = 0.f;
	bPlayingIntro = true;
	NextClipAt = FPlatformTime::Seconds() + 0.4;
	SetMode(uint8(EHoloMode::Greeting));
}

bool AHoloDirector::Say(const FString& WavPath)
{
	FHoloClip C;
	if (!LoadClip(WavPath, C))
	{
		SendEvent(TEXT("error"), FString::Printf(TEXT("\"message\":\"cannot load %s\""), *EscapeJson(FPaths::GetCleanFilename(WavPath))));
		return false;
	}
	StopAll();
	bPlayingIntro = false;
	Queue.Add(MoveTemp(C));
	NextClipAt = FPlatformTime::Seconds();
	SetMode(uint8(EHoloMode::Speaking));
	return true;
}

void AHoloDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	PollCommands();
	const double Now = FPlatformTime::Seconds();

	// Empezar el siguiente clip de la cola
	if (!bActive && Queue.Num() > 0 && NextClipAt >= 0.0 && Now >= NextClipAt)
	{
		FHoloClip C = Queue[0];
		Queue.RemoveAt(0);
		StartClip(C);
	}

	if (bActive)
	{
		const float T = float(Now - ClipStart) + LipLead;
		if (T >= Active.Duration + 0.05f)
		{
			bActive = false;
			SetMouth(0.f, 0.f, 0.f);
			if (Queue.Num() > 0)
			{
				NextClipAt = Now + Queue[0].GapBefore;
			}
			else
			{
				NextClipAt = -1.0;
				SetMode(uint8(EHoloMode::Idle));
				if (bPlayingIntro)
				{
					bPlayingIntro = false;
					bIntroDone = true;
					UE_LOG(LogHoloDirector, Log, TEXT("Presentacion terminada -> reposo"));
					SendEvent(TEXT("intro_done"));
				}
				else
				{
					SendEvent(TEXT("speech_end"));
				}
			}
		}
		else
		{
			// Interpolacion entre los valores de 10 ms
			const float F = FMath::Max(0.f, T) / FrameSec;
			const int32 I0 = FMath::Clamp(int32(F), 0, Active.Open.Num() - 1);
			const int32 I1 = FMath::Min(I0 + 1, Active.Open.Num() - 1);
			const float A = FMath::Frac(F);
			SetMouth(FMath::Lerp(Active.Open[I0], Active.Open[I1], A),
			         FMath::Lerp(Active.Wide[I0], Active.Wide[I1], A),
			         FMath::Lerp(Active.Round[I0], Active.Round[I1], A));
		}
	}

	// Etapa 4: si Python deja de enviar datos de la camara (cerrado o colgado),
	// se olvida a la persona y el indicador de camara se apaga.
	if (UHoloStateSubsystem* St = GetWorld()->GetSubsystem<UHoloStateSubsystem>())
	{
		if (St->bCameraOn && LastFaceMsg > 0.0 && Now - LastFaceMsg > 2.0)
		{
			St->bCameraOn = false;
			St->bFacePresent = false;
		}
	}

	UpdateMouseView(DeltaSeconds);
	DrawStatus();
}

// ================================================================ puente UDP con Python
void AHoloDirector::OpenSockets()
{
	RecvSocket = FUdpSocketBuilder(TEXT("HoloDirectorRecv"))
		.AsNonBlocking()
		.AsReusable()
		.BoundToAddress(FIPv4Address(127, 0, 0, 1))   // solo este ordenador
		.BoundToPort(uint16(ListenPort))
		.WithReceiveBufferSize(64 * 1024)
		.Build();
	SendSocket = FUdpSocketBuilder(TEXT("HoloDirectorSend")).AsNonBlocking().Build();
	UE_LOG(LogHoloDirector, Log, TEXT("Puente Python: escucho en 127.0.0.1:%d, aviso a :%d (%s)"),
		ListenPort, PythonPort, RecvSocket ? TEXT("OK") : TEXT("ERROR"));
}

void AHoloDirector::CloseSockets()
{
	ISocketSubsystem* SS = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (RecvSocket) { RecvSocket->Close(); SS->DestroySocket(RecvSocket); RecvSocket = nullptr; }
	if (SendSocket) { SendSocket->Close(); SS->DestroySocket(SendSocket); SendSocket = nullptr; }
}

void AHoloDirector::PollCommands()
{
	if (!RecvSocket) return;
	ISocketSubsystem* SS = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	TSharedRef<FInternetAddr> From = SS->CreateInternetAddr();
	uint32 Pending = 0;
	int32 Guard = 0;
	while (RecvSocket->HasPendingData(Pending) && Guard++ < 32)
	{
		TArray<uint8> Buf;
		Buf.SetNumUninitialized(FMath::Min<uint32>(FMath::Max<uint32>(Pending, 1), 65507));
		int32 Read = 0;
		if (!RecvSocket->RecvFrom(Buf.GetData(), Buf.Num(), Read, *From) || Read <= 0) break;
		const FString Msg = FString(FUTF8ToTCHAR(reinterpret_cast<const ANSICHAR*>(Buf.GetData()), Read));
		LastPythonMsg = FPlatformTime::Seconds();
		HandleCommand(Msg);
	}
}

void AHoloDirector::HandleCommand(const FString& Json)
{
	TSharedPtr<FJsonObject> Obj;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Obj) || !Obj.IsValid())
	{
		UE_LOG(LogHoloDirector, Warning, TEXT("Mensaje no valido de Python: %s"), *Json);
		return;
	}
	const FString Cmd = Obj->GetStringField(TEXT("cmd"));
	if (Cmd == TEXT("mode"))
	{
		const FString M = Obj->GetStringField(TEXT("mode"));
		if (bActive || Queue.Num() > 0) return;   // nunca interrumpir la voz con un cambio de estado
		if (M == TEXT("listening"))      SetMode(uint8(EHoloMode::Listening));
		else if (M == TEXT("thinking"))  SetMode(uint8(EHoloMode::Thinking));
		else                             SetMode(uint8(EHoloMode::Idle));
	}
	else if (Cmd == TEXT("say"))
	{
		Say(Obj->GetStringField(TEXT("file")));
	}
	else if (Cmd == TEXT("intro"))
	{
		ReplayIntro();
	}
	else if (Cmd == TEXT("busy"))
	{
		bGpuBusy = Obj->GetBoolField(TEXT("on"));
		ApplyFpsLimit((LastMode == uint8(EHoloMode::Thinking) || bGpuBusy) ? ThinkingMaxFps : MaxFps);
	}
	else if (Cmd == TEXT("stop"))
	{
		StopAll();
		SetMode(uint8(EHoloMode::Idle));
		SendEvent(TEXT("speech_end"));
	}
	else if (Cmd == TEXT("face"))
	{
		// Etapa 4: solo la posicion aproximada de una cara (nada de imagenes).
		if (UHoloStateSubsystem* St = GetWorld()->GetSubsystem<UHoloStateSubsystem>())
		{
			St->bCameraOn = true;
			St->bFacePresent = Obj->GetBoolField(TEXT("present"));
			if (St->bFacePresent)
			{
				St->FaceX = FMath::Clamp(float(Obj->GetNumberField(TEXT("x"))), -1.f, 1.f);
				St->FaceY = FMath::Clamp(float(Obj->GetNumberField(TEXT("y"))), -1.f, 1.f);
			}
		}
		LastFaceMsg = FPlatformTime::Seconds();
	}
	else if (Cmd == TEXT("camera"))
	{
		if (UHoloStateSubsystem* St = GetWorld()->GetSubsystem<UHoloStateSubsystem>())
		{
			St->bCameraOn = Obj->GetBoolField(TEXT("on"));
			if (!St->bCameraOn) St->bFacePresent = false;
		}
		LastFaceMsg = FPlatformTime::Seconds();
	}
	else if (Cmd == TEXT("status"))
	{
		SendEvent(TEXT("status"), FString::Printf(TEXT("\"speaking\":%s,\"intro_done\":%s"),
			(bActive || Queue.Num() > 0) ? TEXT("true") : TEXT("false"),
			bIntroDone ? TEXT("true") : TEXT("false")));
	}
}

void AHoloDirector::SendEvent(const FString& Event, const FString& ExtraJson)
{
	if (!SendSocket) return;
	ISocketSubsystem* SS = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	TSharedRef<FInternetAddr> To = SS->CreateInternetAddr();
	bool bValid = false;
	To->SetIp(TEXT("127.0.0.1"), bValid);
	To->SetPort(PythonPort);
	const FString Msg = ExtraJson.IsEmpty()
		? FString::Printf(TEXT("{\"event\":\"%s\"}"), *Event)
		: FString::Printf(TEXT("{\"event\":\"%s\",%s}"), *Event, *ExtraJson);
	FTCHARToUTF8 Utf8(*Msg);
	int32 Sent = 0;
	SendSocket->SendTo(reinterpret_cast<const uint8*>(Utf8.Get()), Utf8.Length(), Sent, *To);
}

void AHoloDirector::DrawStatus()
{
	if (!bShowStatus || !GEngine) return;
	const UHoloStateSubsystem* St = GetWorld()->GetSubsystem<UHoloStateSubsystem>();
	if (!St) return;
	FString Text;
	FColor Color(90, 220, 255);
	switch (St->Mode)
	{
	case EHoloMode::Listening: Text = TEXT("● MIC ON - listening / escuchando"); Color = FColor(255, 80, 80); break;
	case EHoloMode::Thinking:  Text = TEXT("... thinking / pensando"); break;
	case EHoloMode::Speaking:  Text = TEXT("speaking / hablando"); break;
	case EHoloMode::Greeting:  Text = TEXT("greeting / saludo"); break;
	default:
		Text = (LastPythonMsg > 0.0 && FPlatformTime::Seconds() - LastPythonMsg < 30.0)
			? TEXT("mic off") : TEXT("mic off (assistant.py not running)");
		break;
	}
	GEngine->AddOnScreenDebugMessage(StatusKey, 0.5f, Color, Text, true, FVector2D(1.1f, 1.1f));

	// Etapa 4: estado de la camara, siempre visible mientras esta encendida.
	if (St->bCameraOn)
	{
		GEngine->AddOnScreenDebugMessage(CameraKey, 0.5f, FColor(255, 170, 60),
			St->bFacePresent ? TEXT("● CAMERA ON / CÁMARA ON - person detected / persona detectada")
			                 : TEXT("● CAMERA ON / CÁMARA ON - nobody / nadie"),
			true, FVector2D(1.0f, 1.0f));
	}
}

// ================================================================ Etapa 5: pantalla completa y raton
void AHoloDirector::SetupMouseView()
{
	// La camara de la escena (Camera_Main) mira al centro de la cara desde 95 cm: ese es el pivote.
	for (TActorIterator<ACameraActor> It(GetWorld()); It; ++It)
	{
		ViewCam = *It;
		break;
	}
	if (!ViewCam.IsValid()) return;
	Rot0 = ViewCam->GetActorRotation();
	Pivot0 = ViewCam->GetActorLocation() + Rot0.Vector() * Dist0;
	ResetView();
	Rot = RotGoal; Pivot = PivotGoal; Dist = DistGoal;
	LastMouseMove = FPlatformTime::Seconds();
}

void AHoloDirector::ResetView()
{
	RotGoal = Rot0;
	PivotGoal = Pivot0;
	DistGoal = Dist0;
}

void AHoloDirector::ZoomIn()  { DistGoal = FMath::Clamp(DistGoal * 0.9f, MinDistance, MaxDistance); }
void AHoloDirector::ZoomOut() { DistGoal = FMath::Clamp(DistGoal / 0.9f, MinDistance, MaxDistance); }

void AHoloDirector::ToggleStatusText()
{
	bShowStatus = !bShowStatus;
	if (!bShowStatus && GEngine)
	{
		GEngine->RemoveOnScreenDebugMessage(StatusKey);
		GEngine->RemoveOnScreenDebugMessage(CameraKey);
	}
}

void AHoloDirector::ToggleFullscreen()
{
	UGameUserSettings* S = GEngine ? GEngine->GetGameUserSettings() : nullptr;
	if (!S) return;
	bFullscreen = !bFullscreen;
	if (bFullscreen)
	{
		S->SetScreenResolution(S->GetDesktopResolution());
		S->SetFullscreenMode(EWindowMode::WindowedFullscreen);   // sin cambiar la resolucion del monitor
	}
	else
	{
		S->SetScreenResolution(FIntPoint(1280, 720));
		S->SetFullscreenMode(EWindowMode::Windowed);
	}
	S->ApplyResolutionSettings(false);
	UE_LOG(LogHoloDirector, Log, TEXT("Pantalla completa: %s"), bFullscreen ? TEXT("SI") : TEXT("NO"));
}

void AHoloDirector::UpdateMouseView(float DeltaSeconds)
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!PC) return;
	const double Now = FPlatformTime::Seconds();

	float MX = 0.f, MY = 0.f;
	if (PC->GetMousePosition(MX, MY))
	{
		const FVector2D M(MX, MY);
		if (LastMouse.X >= 0.f)
		{
			const FVector2D D = M - LastMouse;
			if (!D.IsNearlyZero())
			{
				LastMouseMove = Now;
				if (PC->IsInputKeyDown(EKeys::LeftMouseButton))          // girar alrededor de la cabeza
				{
					RotGoal.Yaw = FMath::Clamp(RotGoal.Yaw + D.X * OrbitSpeed, Rot0.Yaw - MaxYaw, Rot0.Yaw + MaxYaw);
					RotGoal.Pitch = FMath::Clamp(RotGoal.Pitch - D.Y * OrbitSpeed, Rot0.Pitch - MaxPitch, Rot0.Pitch + MaxPitch);
				}
				else if (PC->IsInputKeyDown(EKeys::RightMouseButton))    // desplazar la vista
				{
					const float K = DistGoal * 0.0015f;
					const FRotationMatrix R(RotGoal);
					PivotGoal += (-R.GetUnitAxis(EAxis::Y) * D.X + R.GetUnitAxis(EAxis::Z) * D.Y) * K;
					PivotGoal = Pivot0 + (PivotGoal - Pivot0).GetClampedToMaxSize(40.f);
				}
			}
		}
		LastMouse = M;
	}
	if (PC->IsInputKeyDown(EKeys::LeftMouseButton) || PC->IsInputKeyDown(EKeys::RightMouseButton))
	{
		LastMouseMove = Now;
	}
	// cursor visible solo mientras se usa el raton
	const bool bShow = Now - LastMouseMove < HideCursorAfter;
	if (PC->bShowMouseCursor != bShow)
	{
		PC->bShowMouseCursor = bShow;
	}

	if (!ViewCam.IsValid()) return;
	const float A = FMath::Clamp(DeltaSeconds * 10.f, 0.f, 1.f);   // movimiento suave
	Rot = FMath::Lerp(Rot, RotGoal, A);
	Pivot = FMath::Lerp(Pivot, PivotGoal, A);
	Dist = FMath::Lerp(Dist, DistGoal, A);
	ViewCam->SetActorLocationAndRotation(Pivot - Rot.Vector() * Dist, Rot);
}
