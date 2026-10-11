// SPDX-License-Identifier: MIT
using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// Invoke from an owned isolated Editor. No Asset import/save or provider Apply.
public static class VapbImportAssistantCancellationProbe
{
    const BindingFlags Flags = BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
    [Serializable] public class Result
    {
        public bool window_survives, remaining_entry_exact, a_cancelled, b_prompted,
                    b_state_survives_window_recreation, last_entry_closes, state_restored;
        public string error;
    }
    public static Result Observe()
    {
        var result = new Result();
        Type type = typeof(VapbImportAssistant);
        string path = (string)type.GetProperty("StatePath", Flags).GetValue(null);
        bool existed = File.Exists(path);
        byte[] before = existed ? File.ReadAllBytes(path) : null;
        VapbImportAssistant window = null;
        try
        {
            Type entryType = type.GetNestedType("Entry", Flags);
            object a = Activator.CreateInstance(entryType, true), b = Activator.CreateInstance(entryType, true);
            string nonce = Guid.NewGuid().ToString("N");
            string aId = nonce + "a", bId = nonce + "b";
            entryType.GetField("identity", Flags | BindingFlags.Public).SetValue(a, aId);
            entryType.GetField("identity", Flags | BindingFlags.Public).SetValue(b, bId);
            // Show a real utility window; OnGUI is not needed to invoke the same handler.
            window = ScriptableObject.CreateInstance<VapbImportAssistant>();
            IList entries = (IList)type.GetField("entries", Flags).GetValue(window);
            entries.Add(a); entries.Add(b);
            type.GetMethod("Remember", Flags).Invoke(null, new[] { a, "prompted" });
            type.GetMethod("Remember", Flags).Invoke(null, new[] { b, "prompted" });
            window.ShowUtility();
            type.GetMethod("CancelEntry", Flags).Invoke(window, new[] { a });
            result.window_survives = window != null;
            result.remaining_entry_exact = window != null && entries.Count == 1 && ReferenceEquals(entries[0], b);
            string[] lines = File.ReadAllLines(path);
            result.a_cancelled = lines.Contains(aId + " cancelled");
            result.b_prompted = lines.Contains(bId + " prompted") && !lines.Contains(bId + " cancelled");
            if (window != null) window.Close();
            window = ScriptableObject.CreateInstance<VapbImportAssistant>();
            result.b_state_survives_window_recreation = File.ReadAllLines(path).Contains(bId + " prompted");
            entries = (IList)type.GetField("entries", Flags).GetValue(window);
            entries.Add(b); window.ShowUtility();
            type.GetMethod("CancelEntry", Flags).Invoke(window, new[] { b });
            result.last_entry_closes = window == null;
        }
        catch (Exception error) { result.error = error.ToString(); }
        finally
        {
            if (window != null) window.Close();
            if (existed) File.WriteAllBytes(path, before);
            else if (File.Exists(path)) File.Delete(path);
            result.state_restored = existed ? File.ReadAllBytes(path).SequenceEqual(before) : !File.Exists(path);
        }
        return result;
    }
}
