Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile("test_speech.wav")
$synth.Speak("What is the weather in Kolkata tomorrow?")
$synth.Dispose()
Write-Host "Created test_speech.wav"
