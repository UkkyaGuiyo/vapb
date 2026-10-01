// SPDX-License-Identifier: MIT
using System;
using System.IO;

// Compile with Editor/VapbCorpusPackageCallback.cs; does not require Unity.
public static class CallbackNameRegression
{
    public static int Main()
    {
        string folder = Path.Combine(Path.GetTempPath(), "VapbPublicCallbackControl");
        string requested = Path.Combine(folder, "Public.1.22.unitypackage");
        bool[] controls = {
            VapbCorpusPackageCallback.Matches("Public.1.22", requested),
            VapbCorpusPackageCallback.Matches(Path.Combine(folder, "Public.1.22"), requested),
            VapbCorpusPackageCallback.Matches(requested, requested),
            VapbCorpusPackageCallback.Matches("Public.1.22.UNITYPACKAGE", requested),
            !VapbCorpusPackageCallback.Matches("Public.1", requested),
            !VapbCorpusPackageCallback.Matches("Public.1.21", requested),
            !VapbCorpusPackageCallback.Matches("Unrelated.1.22", requested)
        };
        foreach (bool control in controls)
            if (!control) { Console.WriteLine("CALLBACK_REGRESSION verdict=RED"); return 1; }
        Console.WriteLine("CALLBACK_REGRESSION verdict=PASS controls=" + controls.Length);
        return 0;
    }
}
