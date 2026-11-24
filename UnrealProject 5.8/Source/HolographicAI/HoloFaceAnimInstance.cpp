#include "HoloFaceAnimInstance.h"
#include "HoloStateSubsystem.h"
#include "Animation/AnimNodeBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "AnimationRuntime.h"

DEFINE_LOG_CATEGORY_STATIC(LogHoloFace, Log, All);

// ---------------------------------------------------------------- ajustes
// Todo en un solo sitio para poder retocar la "personalidad" facilmente.
namespace HoloTune
{
	// Parpadeo
	constexpr float BlinkMinInterval = 2.0f;   // segundos
	constexpr float BlinkMaxInterval = 5.0f;
	constexpr float DoubleBlinkChance = 0.12f;

	// Mirada (valores de curva 0..1)
	constexpr float GazeSideRange = 0.28f;
	constexpr float GazeUpRange = 0.08f;
	constexpr float GazeDownMin = 0.22f;
	constexpr float GazeDownMax = 0.40f;
	constexpr float GazeDownChance = 0.18f;
	constexpr float GazeCenterChance = 0.30f;
	constexpr float GazeOmega = 18.f;          // rapidez del movimiento de ojos
	constexpr float BlinkOnSaccadeChance = 0.25f;

	// Cabeza (grados)
	constexpr float YawAmp = 3.0f;
	constexpr float NodAmp = 1.5f;
	constexpr float TiltAmp = 1.8f;
	constexpr float TiltEventAmp = 4.0f;       // inclinacion ocasional
	constexpr float TiltEventChance = 0.12f;
	constexpr float HeadOmega = 1.1f;          // muy lento = suave
	constexpr float HeadFollowGazeDeg = 10.f;
	constexpr float BreathNodDeg = 0.35f;

	// Microexpresiones (0..1)
	constexpr float BrowAmp = 0.10f;
	constexpr float SmileBase = 0.06f;
	constexpr float SmileAmp = 0.04f;

	// Habla (Etapa 2)
	constexpr float JawMax = 0.55f;            // 1.0 seria la boca abierta al maximo
	constexpr float JawAttackOmega = 38.f;     // abre rapido
	constexpr float JawReleaseOmega = 22.f;    // cierra un poco mas despacio
	constexpr float WideMax = 0.35f;
	constexpr float RoundMax = 0.45f;
	constexpr float TalkNodDeg = 1.2f;         // pequeno asentimiento al hablar

	// Saludo
	constexpr float GreetSmile = 0.32f;
	constexpr float GreetBrow = 0.12f;

	// Escuchando / pensando (Etapa 3)
	constexpr float ListenBrow = 0.10f;
	constexpr float ThinkTiltDeg = 4.5f;       // inclinacion de cabeza al pensar
	constexpr float ThinkYawDeg = 2.0f;
	constexpr float ThinkNodUpDeg = 1.5f;      // barbilla un poco hacia arriba
	constexpr float ThinkBrow = 0.08f;

	// Seguir a la persona (Etapa 4)
	// FaceX = +-1 en el borde de la imagen (~+-35 grados con la camara HP Wide Vision).
	constexpr float FaceGazeGainH = 0.32f;     // ojos: unidades de curva por unidad de imagen
	constexpr float FaceGazeGainV = 0.14f;
	constexpr float FaceGazeMax = 0.34f;
	constexpr float FaceHeadYawDeg = 9.f;      // la cabeza gira ademas hacia la persona
	constexpr float FaceHeadNodDeg = 3.f;
	constexpr float FaceLookChanceIdle = 0.65f;// en reposo a veces mira a otro lado
	constexpr float FaceFollowOmega = 6.f;     // suavizado del movimiento de la persona
	// Signo: en la imagen sin espejo, la izquierda de la camara es la derecha del espectador,
	// que es la IZQUIERDA del personaje (curva eyeLookLeft > 0). Si mira al lado contrario: -1.
	constexpr float FaceSideSign = -1.f;
}

// ---------------------------------------------------------------- muelle
void FHoloSpring::Step(float Target, float Omega, float Dt)
{
	// Euler implicito: estable con cualquier Dt, sin oscilaciones.
	const float F = 1.f + 2.f * Dt * Omega;
	const float OO = Omega * Omega;
	const float HOO = Dt * OO;
	const float HHOO = Dt * HOO;
	const float DetInv = 1.f / (F + HHOO);
	const float NewX = (F * X + Dt * V + HHOO * Target) * DetInv;
	const float NewV = (V + HOO * (Target - X)) * DetInv;
	X = NewX;
	V = NewV;
}

// ---------------------------------------------------------------- proxy
void FHoloFaceAnimInstanceProxy::Initialize(UAnimInstance* InAnimInstance)
{
	FAnimInstanceProxy::Initialize(InAnimInstance);
	Rng.Initialize(FPlatformTime::Cycles());
	NextBlinkIn = Rng.FRandRange(1.0f, 2.5f);
	GazeHoldLeft = Rng.FRandRange(0.8f, 2.0f);
	UE_LOG(LogHoloFace, Log, TEXT("HoloFace idle animation started"));
}

void FHoloFaceAnimInstanceProxy::UpdateWander(FHoloWander& W, float Amp, float MinHold, float MaxHold, float Omega, float Dt)
{
	W.TimeLeft -= Dt;
	if (W.TimeLeft <= 0.f)
	{
		W.Target = Rng.FRandRange(-Amp, Amp);
		W.TimeLeft = Rng.FRandRange(MinHold, MaxHold);
	}
	W.Spring.Step(W.Target, Omega, Dt);
}

float FHoloFaceAnimInstanceProxy::BlinkShape(float T, float Close, float Hold, float Open) const
{
	if (T < 0.f) return 0.f;
	if (T < Close)
	{
		const float A = T / Close;
		return A * A * (3.f - 2.f * A);         // cierra acelerando y frena
	}
	T -= Close;
	if (T < Hold) return 1.f;
	T -= Hold;
	if (T < Open)
	{
		const float A = 1.f - T / Open;
		return A * A;                            // abre mas lento, suave al final
	}
	return 0.f;
}

void FHoloFaceAnimInstanceProxy::UpdateBlink(float Dt)
{
	if (BlinkT < 0.f)
	{
		NextBlinkIn -= Dt;
		if (NextBlinkIn <= 0.f)
		{
			BlinkT = 0.f;
			BlinkClose = Rng.FRandRange(0.06f, 0.10f);
			BlinkHold = Rng.FRandRange(0.02f, 0.05f);
			BlinkOpen = Rng.FRandRange(0.14f, 0.24f);
			BlinkAmp = Rng.FRandRange(0.93f, 1.0f);
			BlinkDelayR = Rng.FRandRange(0.f, 0.012f);
			++BlinkCount;
			// Intervalo irregular: mas a menudo cerca de 3 s que en los extremos.
			const float U = 0.5f * (Rng.FRand() + Rng.FRand());
			NextBlinkIn = FMath::Lerp(HoloTune::BlinkMinInterval, HoloTune::BlinkMaxInterval, U);
			if (Rng.FRand() < HoloTune::DoubleBlinkChance)
			{
				NextBlinkIn = Rng.FRandRange(0.25f, 0.45f);   // parpadeo doble
			}
		}
	}
	if (BlinkT >= 0.f)
	{
		BlinkT += Dt;
		BlinkL = BlinkAmp * BlinkShape(BlinkT, BlinkClose, BlinkHold, BlinkOpen);
		BlinkR = BlinkAmp * BlinkShape(BlinkT - BlinkDelayR, BlinkClose, BlinkHold, BlinkOpen);
		if (BlinkT > BlinkClose + BlinkHold + BlinkOpen + BlinkDelayR + 0.01f)
		{
			BlinkT = -1.f;
			BlinkL = BlinkR = 0.f;
		}
	}
}

void FHoloFaceAnimInstanceProxy::UpdateGaze(float Dt)
{
	// --- Etapa 4: direccion hacia la persona (suavizada) y atencion 0..1
	const float FH = FMath::Clamp(HoloTune::FaceSideSign * InFaceX * HoloTune::FaceGazeGainH,
	                              -HoloTune::FaceGazeMax, HoloTune::FaceGazeMax);
	const float FV = FMath::Clamp(-InFaceY * HoloTune::FaceGazeGainV, -0.2f, 0.2f);
	if (InFacePresent)
	{
		FaceH.Step(FH, HoloTune::FaceFollowOmega, Dt);
		FaceV.Step(FV, HoloTune::FaceFollowOmega, Dt);
	}
	const bool bWasPresent = FaceAttn.X > 0.5f;
	FaceAttn.Step(InFacePresent ? 1.f : 0.f, InFacePresent ? 4.f : 1.5f, Dt);
	if (InFacePresent && !bWasPresent && FaceAttn.X > 0.5f && !bThink)
	{
		GazeHoldLeft = 0.f;        // alguien acaba de llegar: mirarle ya
	}
	const bool bFace = InFacePresent && FaceAttn.X > 0.3f;

	GazeHoldLeft -= Dt;
	if (GazeHoldLeft <= 0.f)
	{
		const float OldH = GazeTargetH, OldV = GazeTargetV;
		const float R = Rng.FRand();
		bGazeOnFace = false;
		if (bThink)
		{
			// Pensando: mira hacia arriba y a un lado (casi siempre el mismo lado).
			if (Rng.FRand() < 0.15f) ThinkSide = -ThinkSide;
			GazeTargetH = ThinkSide * Rng.FRandRange(0.12f, 0.28f);
			GazeTargetV = Rng.FRandRange(0.10f, 0.22f);
		}
		else if (bFace && (bFocus || Rng.FRand() < HoloTune::FaceLookChanceIdle))
		{
			// Etapa 4: mira a la persona (con pequenas variaciones entre sus ojos y su boca).
			bGazeOnFace = true;
			FaceOffH = Rng.FRandRange(-0.03f, 0.03f);
			FaceOffV = Rng.FRandRange(-0.03f, 0.015f);
			GazeTargetH = FaceH.X + FaceOffH;
			GazeTargetV = FaceV.X + FaceOffV;
		}
		else if (bFocus)
		{
			// Saludo / escuchando / hablando: mira al frente (al visitante) con movimientos minimos.
			GazeTargetH = Rng.FRandRange(-0.05f, 0.05f);
			GazeTargetV = Rng.FRandRange(-0.03f, 0.02f);
		}
		else if (R < HoloTune::GazeCenterChance)
		{
			GazeTargetH = Rng.FRandRange(-0.04f, 0.04f);
			GazeTargetV = Rng.FRandRange(-0.03f, 0.03f);
		}
		else if (R < HoloTune::GazeCenterChance + HoloTune::GazeDownChance)
		{
			GazeTargetH = Rng.FRandRange(-0.15f, 0.15f);
			GazeTargetV = -Rng.FRandRange(HoloTune::GazeDownMin, HoloTune::GazeDownMax);
		}
		else
		{
			GazeTargetH = Rng.FRandRange(-HoloTune::GazeSideRange, HoloTune::GazeSideRange);
			GazeTargetV = Rng.FRandRange(-0.08f, HoloTune::GazeUpRange);
		}
		// Pausas naturales: a veces corta, a veces larga (mirando a la persona, mas larga).
		GazeHoldLeft = bGazeOnFace ? Rng.FRandRange(1.5f, 4.5f)
			: (Rng.FRand() < 0.3f) ? Rng.FRandRange(0.4f, 1.0f) : Rng.FRandRange(1.2f, 3.8f);

		// Un movimiento grande de ojos a veces va acompanado de un parpadeo.
		const float Jump = FMath::Abs(GazeTargetH - OldH) + FMath::Abs(GazeTargetV - OldV);
		if (Jump > 0.2f && BlinkT < 0.f && NextBlinkIn > 0.6f && Rng.FRand() < HoloTune::BlinkOnSaccadeChance)
		{
			NextBlinkIn = 0.02f;
		}
	}

	// Microsacadas: temblor minimo que hace que los ojos no parezcan congelados.
	MicroLeft -= Dt;
	if (MicroLeft <= 0.f)
	{
		MicroH = Rng.FRandRange(-0.012f, 0.012f);
		MicroV = Rng.FRandRange(-0.008f, 0.008f);
		MicroLeft = Rng.FRandRange(0.3f, 0.9f);
	}

	if (bGazeOnFace)
	{
		if (bFace)
		{
			// la persona se mueve: los ojos la siguen
			GazeTargetH = FaceH.X + FaceOffH;
			GazeTargetV = FaceV.X + FaceOffV;
		}
		else
		{
			bGazeOnFace = false;   // se ha ido: volver pronto a la mirada libre
			GazeHoldLeft = FMath::Min(GazeHoldLeft, Rng.FRandRange(0.3f, 0.9f));
		}
	}

	GazeH.Step(GazeTargetH + MicroH, HoloTune::GazeOmega, Dt);
	GazeV.Step(GazeTargetV + MicroV, HoloTune::GazeOmega, Dt);
}

void FHoloFaceAnimInstanceProxy::UpdateHead(float Dt)
{
	UpdateWander(Yaw, HoloTune::YawAmp, 3.f, 8.f, HoloTune::HeadOmega, Dt);
	UpdateWander(Nod, HoloTune::NodAmp, 4.f, 9.f, HoloTune::HeadOmega, Dt);

	// Inclinacion: normalmente pequena, de vez en cuando algo mas marcada.
	Tilt.TimeLeft -= Dt;
	if (Tilt.TimeLeft <= 0.f)
	{
		const float Amp = (Rng.FRand() < HoloTune::TiltEventChance) ? HoloTune::TiltEventAmp : HoloTune::TiltAmp;
		Tilt.Target = Rng.FRandRange(-Amp, Amp);
		Tilt.TimeLeft = Rng.FRandRange(4.f, 10.f);
	}
	Tilt.Spring.Step(Tilt.Target, HoloTune::HeadOmega * 0.8f, Dt);

	// La cabeza acompana un poco a la mirada, con retraso.
	HeadFollow.Step(GazeH.X, 1.5f, Dt);

	// Respiracion: ciclo de ~4 s cuyo periodo varia un poco en cada respiracion.
	BreathPhase += Dt / BreathPeriod;
	if (BreathPhase >= 1.f)
	{
		BreathPhase -= 1.f;
		BreathPeriod = Rng.FRandRange(3.6f, 4.8f);
	}
	const float Breath = FMath::Sin(BreathPhase * 2.f * PI);

	// --- habla: la boca sigue al audio (abre rapido, cierra algo mas suave)
	const float JawTarget = InMouthOpen * HoloTune::JawMax;
	Jaw.Step(JawTarget, JawTarget > Jaw.X ? HoloTune::JawAttackOmega : HoloTune::JawReleaseOmega, Dt);
	Wide.Step(InMouthWide * HoloTune::WideMax, 30.f, Dt);
	Round.Step(InMouthRound * HoloTune::RoundMax, 25.f, Dt);
	OutJaw = FMath::Max(0.f, Jaw.X);
	OutWide = FMath::Max(0.f, Wide.X);
	OutRound = FMath::Max(0.f, Round.X);

	// --- saludo: transicion suave (~1 s) hacia sonrisa + mirada al frente
	Greet.Step(bGreet ? 1.f : 0.f, 3.0f, Dt);
	Listen.Step(bListen ? 1.f : 0.f, 3.0f, Dt);
	Think.Step(bThink ? 1.f : 0.f, 2.0f, Dt);
	const float G = FMath::Clamp(Greet.X, 0.f, 1.f);
	const float L = FMath::Clamp(Listen.X, 0.f, 1.f);
	const float K = FMath::Clamp(Think.X, 0.f, 1.f);
	// Saludando o escuchando la cabeza se mueve menos (atencion).
	const float Calm = 1.f - 0.5f * FMath::Max(G, L);

	// Etapa 4: con una persona delante, la cabeza tambien se orienta hacia ella.
	const float FA = FMath::Clamp(FaceAttn.X, 0.f, 1.f) * (1.f - 0.6f * K);
	const float FaceYaw = FA * FaceH.X / HoloTune::FaceGazeGainH * HoloTune::FaceHeadYawDeg;
	const float FaceNod = FA * FaceV.X / HoloTune::FaceGazeGainV * HoloTune::FaceHeadNodDeg;

	OutYaw = (Yaw.Spring.X + HeadFollow.X * HoloTune::HeadFollowGazeDeg) * Calm
	       + K * ThinkSide * HoloTune::ThinkYawDeg + FaceYaw;
	OutNod = Nod.Spring.X * Calm + Breath * HoloTune::BreathNodDeg + GazeV.X * 3.f
	       + OutJaw / HoloTune::JawMax * HoloTune::TalkNodDeg * 0.5f
	       - K * HoloTune::ThinkNodUpDeg - FaceNod;
	OutTilt = Tilt.Spring.X * Calm + K * ThinkSide * HoloTune::ThinkTiltDeg;

	UpdateWander(Brow, HoloTune::BrowAmp, 5.f, 14.f, 2.0f, Dt);
	UpdateWander(Smile, HoloTune::SmileAmp, 6.f, 15.f, 1.0f, Dt);
	OutBrow = FMath::Max(0.f, Brow.Spring.X) + G * HoloTune::GreetBrow
	        + L * HoloTune::ListenBrow + K * HoloTune::ThinkBrow;
	// Al hablar la sonrisa baja un poco para no deformar la boca.
	OutSmile = FMath::Max(0.f, HoloTune::SmileBase + Smile.Spring.X)
	         + G * HoloTune::GreetSmile * (1.f - 0.5f * OutJaw / HoloTune::JawMax);
}

void FHoloFaceAnimInstanceProxy::Update(float DeltaSeconds)
{
	const float Dt = FMath::Clamp(DeltaSeconds, 0.f, 0.1f);   // evita saltos tras un tiron
	Time += Dt;

	const EHoloMode Mode = static_cast<EHoloMode>(InMode);
	const bool bWasThink = bThink, bWasFocus = bFocus;
	bGreet = (Mode == EHoloMode::Greeting);
	bListen = (Mode == EHoloMode::Listening);
	bThink = (Mode == EHoloMode::Thinking);
	bFocus = bGreet || bListen || (Mode == EHoloMode::Speaking);
	if (bThink != bWasThink || bFocus != bWasFocus)
	{
		GazeHoldLeft = Rng.FRandRange(0.05f, 0.25f);   // cambio de estado -> nueva mirada pronto
	}
	UpdateBlink(Dt);
	UpdateGaze(Dt);
	UpdateHead(Dt);

	LogTimer += Dt;
	MaxJawSinceLog = FMath::Max(MaxJawSinceLog, OutJaw);
	if (LogTimer > 5.f)
	{
		LogTimer = 0.f;
		UE_LOG(LogHoloFace, Log, TEXT("HoloFace alive: t=%.0fs blinks=%d gaze=(%.2f,%.2f) head yaw=%.2f nod=%.2f tilt=%.2f | mode=%d greet=%.2f listen=%.2f think=%.2f smile=%.2f maxJaw=%.2f | face=%d attn=%.2f faceGaze=(%.2f,%.2f) onFace=%d"),
			Time, BlinkCount, GazeH.X, GazeV.X, OutYaw, OutNod, OutTilt, int32(InMode), Greet.X, Listen.X, Think.X, OutSmile, MaxJawSinceLog,
			InFacePresent ? 1 : 0, FaceAttn.X, FaceH.X, FaceV.X, bGazeOnFace ? 1 : 0);
		MaxJawSinceLog = 0.f;
	}
}

bool FHoloFaceAnimInstanceProxy::Evaluate(FPoseContext& Output)
{
	Output.ResetToRefPose();

	// --- curvas de la cara (las lee RigLogic en ABP_Face_PostProcess)
	FBlendedCurve& C = Output.Curve;
	C.Set(TEXT("CTRL_expressions_eyeBlinkL"), BlinkL);
	C.Set(TEXT("CTRL_expressions_eyeBlinkR"), BlinkR);

	const float H = GazeH.X, V = GazeV.X;
	C.Set(TEXT("CTRL_expressions_eyeLookLeftL"), FMath::Max(0.f, H));
	C.Set(TEXT("CTRL_expressions_eyeLookLeftR"), FMath::Max(0.f, H));
	C.Set(TEXT("CTRL_expressions_eyeLookRightL"), FMath::Max(0.f, -H));
	C.Set(TEXT("CTRL_expressions_eyeLookRightR"), FMath::Max(0.f, -H));
	C.Set(TEXT("CTRL_expressions_eyeLookUpL"), FMath::Max(0.f, V));
	C.Set(TEXT("CTRL_expressions_eyeLookUpR"), FMath::Max(0.f, V));
	C.Set(TEXT("CTRL_expressions_eyeLookDownL"), FMath::Max(0.f, -V));
	C.Set(TEXT("CTRL_expressions_eyeLookDownR"), FMath::Max(0.f, -V));

	C.Set(TEXT("CTRL_expressions_browRaiseInL"), OutBrow);
	C.Set(TEXT("CTRL_expressions_browRaiseInR"), OutBrow);
	C.Set(TEXT("CTRL_expressions_mouthCornerPullL"), OutSmile);
	C.Set(TEXT("CTRL_expressions_mouthCornerPullR"), OutSmile);

	// --- boca (habla)
	C.Set(TEXT("CTRL_expressions_jawOpen"), OutJaw);
	C.Set(TEXT("CTRL_expressions_mouthLowerLipDepressL"), OutJaw * 0.35f);
	C.Set(TEXT("CTRL_expressions_mouthLowerLipDepressR"), OutJaw * 0.35f);
	C.Set(TEXT("CTRL_expressions_mouthUpperLipRaiseL"), OutJaw * 0.15f);
	C.Set(TEXT("CTRL_expressions_mouthUpperLipRaiseR"), OutJaw * 0.15f);
	C.Set(TEXT("CTRL_expressions_mouthStretchL"), OutWide);
	C.Set(TEXT("CTRL_expressions_mouthStretchR"), OutWide);
	C.Set(TEXT("CTRL_expressions_mouthFunnelUL"), OutRound);
	C.Set(TEXT("CTRL_expressions_mouthFunnelUR"), OutRound);
	C.Set(TEXT("CTRL_expressions_mouthFunnelDL"), OutRound);
	C.Set(TEXT("CTRL_expressions_mouthFunnelDR"), OutRound);
	C.Set(TEXT("CTRL_expressions_mouthLipsPurseUL"), OutRound * 0.4f);
	C.Set(TEXT("CTRL_expressions_mouthLipsPurseUR"), OutRound * 0.4f);
	C.Set(TEXT("CTRL_expressions_mouthLipsPurseDL"), OutRound * 0.4f);
	C.Set(TEXT("CTRL_expressions_mouthLipsPurseDR"), OutRound * 0.4f);

	// El giro de la cabeza NO se hace aqui: RigLogic sobrescribe head/neck.
	// Ver UHoloFaceAnimInstance::NativeUpdateAnimation.
	return true;
}

// ---------------------------------------------------------------- hilo de juego
void UHoloFaceAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);

	USkeletalMeshComponent* Comp = GetSkelMeshComponent();
	UWorld* World = GetWorld();

	// Copia el estado (voz/IA) al proxy. Si no hay subsistema, todo sigue en reposo:
	// la animacion autonoma nunca depende de esto.
	if (World)
	{
		if (const UHoloStateSubsystem* St = World->GetSubsystem<UHoloStateSubsystem>())
		{
			Proxy.InMode = static_cast<uint8>(St->Mode);
			Proxy.InMouthOpen = St->MouthOpen;
			Proxy.InMouthWide = St->MouthWide;
			Proxy.InMouthRound = St->MouthRound;
			Proxy.InFacePresent = St->bFacePresent;
			Proxy.InFaceX = St->FaceX;
			Proxy.InFaceY = St->FaceY;
		}
	}
	if (!Comp || !World || !World->IsGameWorld() || Comp->Mobility != EComponentMobility::Movable)
	{
		return;
	}

	if (!bHeadInit)
	{
		InitialWorld = Comp->GetComponentTransform();
		// Pivote: base del cuello. Asi la cabeza gira como una cabeza real,
		// no alrededor de los pies del modelo.
		// Se calcula con el pose de referencia del esqueleto, porque en el primer
		// fotograma los huesos todavia no estan evaluados (darian 0,0,0).
		USkeletalMesh* Mesh = Comp->GetSkeletalMeshAsset();
		if (!Mesh) return;
		const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
		FName PivotBone = TEXT("neck_01");
		int32 BoneIdx = Ref.FindBoneIndex(PivotBone);
		if (BoneIdx == INDEX_NONE) { PivotBone = TEXT("head"); BoneIdx = Ref.FindBoneIndex(PivotBone); }
		if (BoneIdx == INDEX_NONE) return;
		const FVector PivotCS = FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, BoneIdx).GetLocation();
		PivotWorld = InitialWorld.TransformPosition(PivotCS);
		bHeadInit = true;
		UE_LOG(LogHoloFace, Log, TEXT("HoloFace head pivot: %s at %s"), *PivotBone.ToString(), *PivotWorld.ToString());
	}

	// La cara mira hacia +Y en espacio de componente:
	// giro = eje Z, asentir = eje X, inclinar hacia el hombro = eje Y.
	// OutYaw > 0 = hacia el mismo lado que eyeLookLeft (izquierda del personaje). En este
	// componente eso es un giro NEGATIVO sobre Z (comprobado con capturas en la Etapa 4).
	const FQuat LocalQ =
		FQuat(FVector::UpVector, FMath::DegreesToRadians(-Proxy.OutYaw)) *
		FQuat(FVector(1, 0, 0), FMath::DegreesToRadians(Proxy.OutNod)) *
		FQuat(FVector(0, 1, 0), FMath::DegreesToRadians(Proxy.OutTilt));

	const FQuat InitRot = InitialWorld.GetRotation();
	const FQuat WorldQ = InitRot * LocalQ * InitRot.Inverse();
	const FVector NewLoc = PivotWorld + WorldQ.RotateVector(InitialWorld.GetLocation() - PivotWorld);
	Comp->SetWorldLocationAndRotation(NewLoc, WorldQ * InitRot);
}
