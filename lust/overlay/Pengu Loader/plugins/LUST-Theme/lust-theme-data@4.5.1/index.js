// Lust: stands in for the lust-theme-data package the theme used to load from
// jsdelivr at every start. Nothing here talks to a server: no tracking, no cloud
// backup, no icon upload. The theme skips icon sync when those calls are missing.
const offline = async () => ({ success: false, data: null, message: "Not available in Lust" })

window.lustthemeApi = {
    readBackup: offline,
    writeBackup: offline,
    deleteBackup: offline,
}
