using UnrealBuildTool;

public class HolographicAITarget : TargetRules
{
	public HolographicAITarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("HolographicAI");
	}
}
