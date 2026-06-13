# Detect the Windows version / edition.
# Returns a string like "windows-11", "windows-10", "windows-server-2022", "windows-unknown".

function Detect-Os {
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        $caption = $os.Caption
        # Examples:
        #   "Microsoft Windows 11 Professionnel"
        #   "Microsoft Windows 10 Famille"
        #   "Microsoft Windows Server 2022 Datacenter"
        switch -Wildcard ($caption) {
            '*Windows 11*' { return "windows-11" }
            '*Windows 10*' { return "windows-10" }
            '*Server 2022*' { return "windows-server-2022" }
            '*Server 2019*' { return "windows-server-2019" }
            '*Server 2016*' { return "windows-server-2016" }
            '*Windows 8*'  { return "windows-8" }
            '*Windows 7*'  { return "windows-7" }
            default        { return "windows-unknown ($caption)" }
        }
    } catch {
        return "windows-unknown (Win32_OperatingSystem unavailable)"
    }
}
