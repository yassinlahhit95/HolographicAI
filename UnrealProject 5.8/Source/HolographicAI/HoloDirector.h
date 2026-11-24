// Director: voz del personaje y puente con Python.
//
// Etapa 2: reproduce la presentacion (ingles y luego espanol) al arrancar, mueve la
//          boca segun el audio y la repite con la tecla R.
// Etapa 3: escucha ordenes de Python por UDP local (127.0.0.1, solo este PC):
//            {"cmd":"mode","mode":"listening"|"thinking"|"idle"}
//            {"cmd":"say","file":"C:/.../respuesta.wav"}
//            {"cmd":"intro"}   {"cmd":"stop"}   {"cmd":"status"}
//          y avisa a Python (puerto PythonPort):
//            {"event":"ready"|"intro_done"|"speech_start"|"speech_end"|"status", ...}
//
// La animacion autonoma de la cara NO depende de nada de esto.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HoloDirector.generated.h"

class UAudioComponent;
class USoundWaveProcedural;
class FSocket;

USTRUCT()
struct FHoloClip
{
	GENERATED_BODY()

	FString Name;
	TArray<uint8> Pcm;          // 16 bits con signo
	int32 SampleRate = 0;
	int32 NumChannels = 1;
	float Duration = 0.f;
	float GapBefore = 0.f;      // pausa antes de este clip (segundos)

	// Analisis para la boca, un valor cada 10 ms
	TArray<float> Open;
	TArray<float> Wide;
	TArray<float> Round;
};

UCLASS()
class HOLOGRAPHICAI_API AHoloDirector : public AActor
{
	GENERATED_BODY()

public:
	AHoloDirector();

	/** Vuelve a reproducir la presentacion completa (tecla R o {"cmd":"intro"}). */
	UFUNCTION(BlueprintCallable, Category = "Holo")
	void ReplayIntro();

	/** Reproduce un WAV cualquiera (respuesta de la IA). */
	UFUNCTION(BlueprintCallable, Category = "Holo")
	bool Say(const FString& WavPath);

	/** Segundos de espera tras arrancar (deja que la escena se estabilice). */
	UPROPERTY(EditAnywhere, Category = "Holo")
	float StartDelay = 2.0f;

	/** Pausa entre el espanol y el ingles. */
	UPROPERTY(EditAnywhere, Category = "Holo")
	float GapBetweenClips = 0.8f;

	UPROPERTY(EditAnywhere, Category = "Holo")
	float Volume = 0.9f;

	/** >0 adelanta la boca respecto al sonido (segundos). */
	UPROPERTY(EditAnywhere, Category = "Holo")
	float LipLead = 0.0f;

	/** Archivos en la carpeta Voice del proyecto, en orden. */
	UPROPERTY(EditAnywhere, Category = "Holo")
	TArray<FString> IntroFiles = { TEXT("intro_es.wav"), TEXT("intro_en.wav") };

	/** Puertos UDP locales: Unreal escucha en ListenPort y avisa a Python en PythonPort. */
	UPROPERTY(EditAnywhere, Category = "Holo")
	int32 ListenPort = 7810;

	UPROPERTY(EditAnywhere, Category = "Holo")
	int32 PythonPort = 7811;

	/** Limite de FPS normal. Sin limite Unreal usa el 96% de la GPU y la voz (Chatterbox)
	 *  tarda 7 veces mas en generarse. */
	UPROPERTY(EditAnywhere, Category = "Holo")
	int32 MaxFps = 60;

	/** Limite de FPS mientras piensa (la GPU genera la voz en ese momento). */
	UPROPERTY(EditAnywhere, Category = "Holo")
	int32 ThinkingMaxFps = 30;

	// --- Vista con el raton (Etapa 5): arrastrar = girar, rueda = zoom, boton derecho = desplazar,
	//     clic central / C = vista inicial, doble clic / F11 = pantalla completa.
	UPROPERTY(EditAnywhere, Category = "Holo|Vista")
	float OrbitSpeed = 0.25f;          // grados por pixel
	UPROPERTY(EditAnywhere, Category = "Holo|Vista")
	float MaxYaw = 80.f;               // giro maximo a cada lado
	UPROPERTY(EditAnywhere, Category = "Holo|Vista")
	float MaxPitch = 35.f;
	UPROPERTY(EditAnywhere, Category = "Holo|Vista")
	float MinDistance = 40.f;          // cm (zoom)
	UPROPERTY(EditAnywhere, Category = "Holo|Vista")
	float MaxDistance = 250.f;
	UPROPERTY(EditAnywhere, Category = "Holo|Vista")
	float HideCursorAfter = 3.f;       // s sin mover el raton -> cursor oculto

	/** Alterna ventana / pantalla completa (F11, doble clic o -holofull al arrancar). */
	UFUNCTION(BlueprintCallable, Category = "Holo")
	void ToggleFullscreen();

	/** Vuelve a la vista inicial de la camara (clic central o C). */
	UFUNCTION(BlueprintCallable, Category = "Holo")
	void ResetView();

	/** Muestra en pantalla el estado (microfono activo, pensando...). */
	UPROPERTY(EditAnywhere, Category = "Holo")
	bool bShowStatus = true;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	bool LoadClip(const FString& Path, FHoloClip& Out);
	void AnalyzeClip(FHoloClip& Clip);
	void StartClip(const FHoloClip& Clip);
	void StopAll();
	void SetMouth(float Open, float Wide, float Round);
	void SetMode(uint8 NewMode);
	void ApplyFpsLimit(int32 Fps);
	/** true mientras Python genera voz en la GPU (comando "busy"): FPS limitados aunque este hablando. */
	bool bGpuBusy = false;
	uint8 LastMode = 0;

	// --- puente UDP
	void OpenSockets();
	void CloseSockets();
	void PollCommands();
	void HandleCommand(const FString& Json);
	void SendEvent(const FString& Event, const FString& ExtraJson = FString());
	void DrawStatus();

	TArray<FHoloClip> IntroClips;

	/** Cola de clips por reproducir y el que suena ahora. */
	TArray<FHoloClip> Queue;
	FHoloClip Active;
	bool bActive = false;
	bool bPlayingIntro = false;
	bool bIntroDone = false;
	double ClipStart = 0.0;      // FPlatformTime::Seconds al empezar
	double NextClipAt = -1.0;    // hora de empezar el siguiente clip de la cola

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Audio;

	UPROPERTY(Transient)
	TObjectPtr<USoundWaveProcedural> Wave;

	FSocket* RecvSocket = nullptr;
	FSocket* SendSocket = nullptr;
	double LastPythonMsg = -1.0;
	double LastFaceMsg = -1.0;

	// --- vista con el raton
	void SetupMouseView();
	void UpdateMouseView(float DeltaSeconds);
	void ZoomIn();
	void ZoomOut();
	void ToggleStatusText();
	TWeakObjectPtr<AActor> ViewCam;
	FVector Pivot0 = FVector::ZeroVector, Pivot = FVector::ZeroVector, PivotGoal = FVector::ZeroVector;
	FRotator Rot0 = FRotator::ZeroRotator, Rot = FRotator::ZeroRotator, RotGoal = FRotator::ZeroRotator;
	float Dist0 = 95.f, Dist = 95.f, DistGoal = 95.f;
	FVector2D LastMouse = FVector2D(-1.f, -1.f);
	double LastMouseMove = 0.0;
	bool bFullscreen = false;     // Etapa 4: ultimo dato de la camara
};
