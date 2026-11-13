"""Síntesis local con las voces de escritorio de Windows."""
import subprocess

_SCRIPT = """
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Speech
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($env:JARVIS_WINDOWS_VOICE) {
        $voice.SelectVoice($env:JARVIS_WINDOWS_VOICE)
    } else {
        $spanish = @($voice.GetInstalledVoices() | Where-Object {
            $_.Enabled -and $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq 'es'
        } | Sort-Object @{Expression = { $_.VoiceInfo.Culture.Name -ne 'es-MX' }},
                        @{Expression = { $_.VoiceInfo.Gender -ne 'Male' }})
        if ($spanish.Count -eq 0) {
            throw 'Instala una voz de escritorio en español en Windows (Text-to-speech).'
        }
        $voice.SelectVoice($spanish[0].VoiceInfo.Name)
    }
    $voice.Speak([Console]::In.ReadToEnd())
} finally {
    $voice.Dispose()
}
"""


class WindowsVoice:
    def speak(self, text):
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT],
                input=text.encode("utf-8"), check=True, capture_output=True,
            )
        except subprocess.CalledProcessError as error:
            raise ValueError(
                "Windows no pudo reproducir la voz. Revisa las voces instaladas "
                "en español y el nombre en JARVIS_WINDOWS_VOICE. "
                + error.stderr.decode("utf-8", errors="replace").strip()
            ) from error
