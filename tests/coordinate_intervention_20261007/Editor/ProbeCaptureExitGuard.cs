using System;
using System.IO;

internal static class ProbeCaptureExitGuard
{
    public static void Run(Func<int?> capture, Action<Exception> recordFailure,
        Action<Exception> reportRecordFailure, Action<int> exit)
    {
        int? exitCode = null;
        try
        {
            exitCode = capture();
        }
        catch (Exception exception)
        {
            exitCode = 1;
            try
            {
                recordFailure(exception);
            }
            catch (Exception recordException)
            {
                try { reportRecordFailure(recordException); }
                catch { /* Reporting and file errors must not skip the Editor exit callback. */ }
            }
        }
        finally
        {
            if (exitCode.HasValue) exit(exitCode.Value);
        }
    }

    public static string RequiredArgument(string[] arguments, string name)
    {
        int index = Array.IndexOf(arguments, name);
        if (index < 0 || index + 1 >= arguments.Length)
            throw new InvalidOperationException("ARGUMENT_MISSING:" + name);
        return arguments[index + 1];
    }

    public static void TryRecordFailure(string path, string contents,
        Action<string, string> writeNew, Action<Exception> reportWriteFailure)
    {
        if (string.IsNullOrWhiteSpace(path) || File.Exists(path)) return;
        try { writeNew(path, contents); }
        catch (Exception exception) { reportWriteFailure(exception); }
    }
}
