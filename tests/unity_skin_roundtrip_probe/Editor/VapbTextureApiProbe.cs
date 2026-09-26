using System;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

public static class VapbTextureApiProbe
{
    [Serializable] private class Source { public string texture_guid; public string material_guid; public string material_file_id; }
    [Serializable] private class Expected { public string original_sha256; public string edited_sha256; public string meta_sha256; public bool output_meta_same; }
    [Serializable] private class Report
    {
        public bool pass, guid_same, meta_same, bytes_edited, material_bound, material_id_same, pixel_changed;
        public string error;
    }
    private static string Project(string name) { return Path.Combine(Path.GetDirectoryName(Application.dataPath), name); }
    private static string Disk(string assetPath) { return Path.Combine(Application.dataPath, assetPath.Substring(7).Replace('/', Path.DirectorySeparatorChar)); }
    private static string Hash(byte[] data)
    {
        using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(data)).Replace("-", "").ToLowerInvariant();
    }
    public static void Run()
    {
        var report = new Report { error = "UNEXPECTED_EXCEPTION" };
        try
        {
            var source = JsonUtility.FromJson<Source>(File.ReadAllText(Project("SourceInfo.json")));
            var expected = JsonUtility.FromJson<Expected>(File.ReadAllText(Project("TextureExpected.json")));
            string texturePath = AssetDatabase.GUIDToAssetPath(source.texture_guid);
            string materialPath = AssetDatabase.GUIDToAssetPath(source.material_guid);
            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
            Material material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            report.guid_same = texture != null && texturePath != null &&
                AssetDatabase.AssetPathToGUID(texturePath) == source.texture_guid;
            report.meta_same = report.guid_same && expected.output_meta_same &&
                Hash(File.ReadAllBytes(Disk(texturePath) + ".meta")) == expected.meta_sha256;
            byte[] editedBytes = File.ReadAllBytes(Disk(texturePath));
            report.bytes_edited = Hash(editedBytes) == expected.edited_sha256 &&
                Hash(editedBytes) != expected.original_sha256;
            report.material_bound = material != null && material.mainTexture == texture;
            report.material_id_same = material != null &&
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(material, out string materialGuid, out long materialId) &&
                materialGuid == source.material_guid && materialId.ToString(System.Globalization.CultureInfo.InvariantCulture) == source.material_file_id;
            var original = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            var edited = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            try
            {
                bool originalLoaded = ImageConversion.LoadImage(original, File.ReadAllBytes(Project("OriginalTexture.png")));
                bool editedLoaded = ImageConversion.LoadImage(edited, editedBytes);
                report.pixel_changed = originalLoaded && editedLoaded && original.width > 0 && original.height > 0 &&
                    original.width == edited.width && original.height == edited.height &&
                    Math.Abs(original.GetPixel(0, 0).r - edited.GetPixel(0, 0).r) > 0.1f;
            }
            finally { UnityEngine.Object.DestroyImmediate(original); UnityEngine.Object.DestroyImmediate(edited); }
            report.pass = report.guid_same && report.meta_same && report.bytes_edited && report.material_bound &&
                report.material_id_same && report.pixel_changed;
            report.error = report.pass ? "NONE" : "ASSERTION_FAILED";
        }
        catch { report.error = "UNEXPECTED_EXCEPTION"; }
        File.WriteAllText(Project("TextureApiResult.json"), JsonUtility.ToJson(report, true));
        EditorApplication.Exit(report.pass ? 0 : 1);
    }
}
