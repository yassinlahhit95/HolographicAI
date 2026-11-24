// Estado compartido del personaje: lo escribe el "director" (voz / mas adelante la IA)
// y lo lee la animacion de la cara. Separar esto garantiza que la animacion
// autonoma (parpadeo, ojos, cabeza) sigue funcionando pase lo que pase con la voz o la IA.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "HoloStateSubsystem.generated.h"

UENUM(BlueprintType)
enum class EHoloMode : uint8
{
	Idle,
	Greeting,
	Listening,   // Etapa 3
	Thinking,    // Etapa 3
	Speaking,    // Etapa 3
};

UCLASS()
class HOLOGRAPHICAI_API UHoloStateSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	EHoloMode Mode = EHoloMode::Idle;

	/** 0..1 apertura de la boca (de la envolvente del audio). */
	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	float MouthOpen = 0.f;

	/** 0..1 boca ancha (sonidos tipo "s", "f", "i"). */
	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	float MouthWide = 0.f;

	/** 0..1 boca redondeada (sonidos tipo "o", "u"). */
	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	float MouthRound = 0.f;

	// --- Etapa 4: webcam (solo posicion de una cara; nunca imagenes ni identidad)

	/** La camara esta encendida (lo indica Python). */
	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	bool bCameraOn = false;

	/** Hay una persona delante de la camara. */
	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	bool bFacePresent = false;

	/** Posicion de la cara en la imagen de la camara: -1 izquierda .. +1 derecha,
	 *  -1 arriba .. +1 abajo (imagen sin espejo, tal como la ve la camara). */
	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	float FaceX = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "Holo")
	float FaceY = 0.f;
};
