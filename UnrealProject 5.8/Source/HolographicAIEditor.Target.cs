using UnrealBuildTool;

public class HolographicAIEditorTarget : TargetRules
{
	public HolographicAIEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("HolographicAI");
	}
}
