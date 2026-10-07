using System;
using System.IO;

internal static class TestProbeCaptureExitGuard
{
    private static int failures;

    private static void Check(bool condition, string name)
    {
        if (condition) return;
        failures++;
        Console.Error.WriteLine("FAIL " + name);
    }

    private static int Main()
    {
        MissingResultArgumentStillExits();
        FailureRecordSerializationErrorStillExits();
        FailureRecordWriteErrorStillExits();
        ExistingResultIsNeverOverwritten();
        DeferredCaptureDoesNotExit();
        Console.WriteLine("PROBE_EXIT_GUARD_TESTS=" + (failures == 0 ? "PASS" : "FAIL")
            + " scenarios=5 failures=" + failures);
        return failures == 0 ? 0 : 1;
    }

    private static void MissingResultArgumentStillExits()
    {
        int exitCalls = 0;
        int exitCode = 0;
        int writeCalls = 0;
        string resultPath = null;
        ProbeCaptureExitGuard.Run(
            delegate
            {
                resultPath = ProbeCaptureExitGuard.RequiredArgument(new string[0], "-vapbCoordinateResult");
                return 0;
            },
            delegate(Exception error)
            {
                ProbeCaptureExitGuard.TryRecordFailure(resultPath, "failure",
                    delegate(string path, string contents) { writeCalls++; File.WriteAllText(path, contents); },
                    delegate(Exception ignored) { });
            },
            delegate(Exception ignored) { },
            delegate(int code) { exitCalls++; exitCode = code; });
        Check(exitCalls == 1 && exitCode == 1, "missing result argument exits with failure");
        Check(resultPath == null, "missing result argument has no guessed output path");
        Check(writeCalls == 0, "missing result argument does not attempt an output write");
    }

    private static void FailureRecordWriteErrorStillExits()
    {
        int exitCalls = 0;
        int exitCode = 0;
        int writeErrors = 0;
        int reportErrors = 0;
        ProbeCaptureExitGuard.Run(
            delegate { throw new IOException("primary capture failure"); },
            delegate(Exception error)
            {
                ProbeCaptureExitGuard.TryRecordFailure("unwritable-result.json", "failure",
                    delegate(string path, string contents) { throw new UnauthorizedAccessException("simulated denial"); },
                    delegate(Exception writeError)
                    {
                        writeErrors++;
                        throw new InvalidOperationException("simulated failure reporter error");
                    });
            },
            delegate(Exception reportError)
            {
                reportErrors++;
                throw new InvalidOperationException("simulated emergency logger error");
            },
            delegate(int code) { exitCalls++; exitCode = code; });
        Check(exitCalls == 1 && exitCode == 1, "failure record write error still exits");
        Check(writeErrors == 1, "failure record write error is reported");
        Check(reportErrors == 1, "failure reporter error is contained before exit");
    }

    private static void FailureRecordSerializationErrorStillExits()
    {
        int exitCalls = 0;
        int exitCode = 0;
        int reportErrors = 0;
        ProbeCaptureExitGuard.Run(
            delegate { throw new IOException("primary capture failure"); },
            delegate(Exception error) { throw new InvalidOperationException("simulated serialization failure"); },
            delegate(Exception reportError) { reportErrors++; },
            delegate(int code) { exitCalls++; exitCode = code; });
        Check(exitCalls == 1 && exitCode == 1, "failure record serialization error still exits");
        Check(reportErrors == 1, "failure record serialization error is reported");
    }

    private static void ExistingResultIsNeverOverwritten()
    {
        string resultPath = Path.Combine(Environment.CurrentDirectory,
            "vapb-probe-existing-" + Guid.NewGuid().ToString("N") + ".json");
        const string original = "preserve-this-result";
        File.WriteAllText(resultPath, original);
        int exitCalls = 0;
        int exitCode = 0;
        ProbeCaptureExitGuard.Run(
            delegate
            {
                using (new FileStream(resultPath, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { }
                return 0;
            },
            delegate(Exception error)
            {
                ProbeCaptureExitGuard.TryRecordFailure(resultPath, "replacement-must-not-be-written",
                    delegate(string path, string contents)
                    {
                        using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                        using (var writer = new StreamWriter(stream)) writer.Write(contents);
                    },
                    delegate(Exception ignored) { });
            },
            delegate(Exception ignored) { },
            delegate(int code) { exitCalls++; exitCode = code; });
        Check(exitCalls == 1 && exitCode == 1, "existing result failure still exits");
        Check(File.ReadAllText(resultPath) == original, "existing result bytes remain unchanged");
        File.Delete(resultPath);
    }

    private static void DeferredCaptureDoesNotExit()
    {
        int exitCalls = 0;
        ProbeCaptureExitGuard.Run(
            delegate { return null; },
            delegate(Exception ignored) { },
            delegate(Exception ignored) { },
            delegate(int ignored) { exitCalls++; });
        Check(exitCalls == 0, "deferred import wait keeps Editor open");
    }
}
