// Animacion autonoma (idle) de la cabeza holografica.
// Funciona sola dentro de Unreal: no depende de Python, de la IA ni de internet.
//
// Escribe las curvas de control del MetaHuman (CTRL_expressions_*) y gira
// los huesos del cuello/cabeza. El AnimBP de post-proceso del MetaHuman
// (ABP_Face_PostProcess, con RigLogic) convierte esas curvas en movimiento real
// de parpados, ojos y cejas.

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "HoloFaceAnimInstance.generated.h"

/** Muelle criticamente amortiguado: mueve un valor hacia su objetivo sin saltos. */
struct FHoloSpring
{
	float X = 0.f;
	float V = 0.f;
	void Step(float Target, float Omega, float Dt);
};

/** Valor que cambia de objetivo aleatoriamente cada pocos segundos y se mueve suave hacia el. */
struct FHoloWander
{
	FHoloSpring Spring;
	float Target = 0.f;
	float TimeLeft = 0.f;
};

USTRUCT()
struct HOLOGRAPHICAI_API FHoloFaceAnimInstanceProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FHoloFaceAnimInstanceProxy() {}
	FHoloFaceAnimInstanceProxy(UAnimInstance* InAnimInstance) : FAnimInstanceProxy(InAnimInstance) {}

protected:
	virtual void Initialize(UAnimInstance* InAnimInstance) override;
	virtual void Update(float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

private:
	void UpdateBlink(float Dt);
	void UpdateGaze(float Dt);
	void UpdateHead(float Dt);
	void UpdateWander(FHoloWander& W, float Amp, float MinHold, float MaxHold, float Omega, float Dt);
	float BlinkShape(float T, float Close, float Hold, float Open) const;

	FRandomStream Rng;
	float Time = 0.f;

	// --- parpadeo
	float NextBlinkIn = 2.f;
	float BlinkT = -1.f;            // <0: no esta parpadeando
	float BlinkClose = 0.08f, BlinkHold = 0.03f, BlinkOpen = 0.18f;
	float BlinkAmp = 1.f;
	float BlinkDelayR = 0.f;        // pequeno desfase entre ojos
	float BlinkL = 0.f, BlinkR = 0.f;

	// --- mirada (H: + izquierda / - derecha, V: + arriba / - abajo)
	float GazeTargetH = 0.f, GazeTargetV = 0.f;
	float GazeHoldLeft = 1.f;
	float MicroLeft = 0.5f;
	float MicroH = 0.f, MicroV = 0.f;
	FHoloSpring GazeH, GazeV;
	FHoloSpring HeadFollow;         // la cabeza sigue un poco a los ojos

	// --- cabeza (grados)
	FHoloWander Yaw, Nod, Tilt;
	float BreathPhase = 0.f;
	float BreathPeriod = 4.2f;

	// --- microexpresiones
	FHoloWander Brow;
	FHoloWander Smile;

	// --- entradas desde UHoloStateSubsystem (se copian en el hilo de juego)
	uint8 InMode = 0;               // EHoloMode (Idle, Greeting, Listening, Thinking, Speaking)
	float InMouthOpen = 0.f, InMouthWide = 0.f, InMouthRound = 0.f;
	bool InFacePresent = false;     // Etapa 4: persona delante de la camara
	float InFaceX = 0.f, InFaceY = 0.f;

	// Etapa 4: la mirada sigue a la persona
	FHoloSpring FaceH, FaceV;       // direccion suavizada hacia la cara (unidades de curva de ojos)
	FHoloSpring FaceAttn;           // 0..1 atencion a la persona (sube/baja suave)
	bool bGazeOnFace = false;       // el objetivo actual de la mirada es la cara
	float FaceOffH = 0.f, FaceOffV = 0.f;

	// --- boca y saludo (suavizados)
	FHoloSpring Jaw, Wide, Round;
	FHoloSpring Greet;              // 0..1 cuanto "modo saludo" hay
	FHoloSpring Listen;             // 0..1 atento (escuchando)
	FHoloSpring Think;              // 0..1 pensando
	bool bFocus = false, bGreet = false, bListen = false, bThink = false;
	float ThinkSide = 1.f;          // hacia que lado mira al pensar

	// Valores finales que se aplican en Evaluate
	float OutYaw = 0.f, OutNod = 0.f, OutTilt = 0.f;
	float OutBrow = 0.f, OutSmile = 0.f;
	float OutJaw = 0.f, OutWide = 0.f, OutRound = 0.f;

	float LogTimer = 0.f;
	float MaxJawSinceLog = 0.f;
	int32 BlinkCount = 0;

	friend class UHoloFaceAnimInstance;
};

UCLASS(Transient, Blueprintable)
class HOLOGRAPHICAI_API UHoloFaceAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

protected:
	// Mueve la cabeza entera girando sobre el cuello. Se hace aqui (hilo de juego)
	// porque RigLogic del MetaHuman sobrescribe los huesos head/neck del pose.
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;

private:
	UPROPERTY(Transient)
	FHoloFaceAnimInstanceProxy Proxy;

	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return &Proxy; }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override {}

	bool bHeadInit = false;
	FTransform InitialWorld;
	FVector PivotWorld = FVector::ZeroVector;

	friend struct FHoloFaceAnimInstanceProxy;
};
