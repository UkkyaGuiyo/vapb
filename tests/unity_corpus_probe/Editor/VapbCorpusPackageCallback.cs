// SPDX-License-Identifier: MIT
using System;
using System.IO;

// Invocation tracking only; callback labels never establish source identity.
public static class VapbCorpusPackageCallback
{
    public static bool Matches(string callbackPackageName, string requestedPackagePath)
    {
        string basename = Path.GetFileName(callbackPackageName);
        const string suffix = ".unitypackage";
        if (basename.EndsWith(suffix, StringComparison.OrdinalIgnoreCase))
            basename = basename.Substring(0, basename.Length - suffix.Length);
        return String.Equals(basename, Path.GetFileNameWithoutExtension(requestedPackagePath),
                             StringComparison.OrdinalIgnoreCase);
    }
}
