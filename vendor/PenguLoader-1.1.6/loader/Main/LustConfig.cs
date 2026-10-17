using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;

namespace PenguLoader.Main
{
    // Lust-only adapter: the loader remains official, but Lust needs the core
    // activation state mirrored into its existing config.ini.
    internal static class LustConfig
    {
        // Lust passes its config.ini: the desktop user's, which core.dll reads in
        // the League client. This process runs elevated, and when Lust was
        // elevated with another account, LocalApplicationData is that account's.
        private static string ConfigPath
        {
            get
            {
                var fromLust = Environment.GetEnvironmentVariable("LUST_CONFIG_PATH");
                if (!string.IsNullOrWhiteSpace(fromLust))
                    return fromLust;

                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "Lust",
                    "config.ini");
            }
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool WritePrivateProfileString(
            string section,
            string key,
            string value,
            string filePath);

        public static void SetLoaderState(bool active)
        {
            var directory = Path.GetDirectoryName(ConfigPath);
            if (!Directory.Exists(directory))
                Directory.CreateDirectory(directory);

            var loaderPath = active
                ? AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                : string.Empty;

            if (!WritePrivateProfileString("General", "disabled", active ? "0" : "1", ConfigPath) ||
                !WritePrivateProfileString("General", "loaderpath", loaderPath, ConfigPath))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "Could not update Lust config.ini.");
            }
        }
    }
}
