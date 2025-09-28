import speech_recognition as sr

def speech_to_text():
    # Initialize recognizer
    recognizer = sr.Recognizer()

    # Use microphone as source
    with sr.Microphone() as source:
        print("Adjusting for background noise... Please wait")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Say something...")

        # Capture the audio
        audio = recognizer.listen(source)

    try:
        # Recognize speech using Google Web Speech API
        text = recognizer.recognize_google(audio)
        print("You said: " + text)

    except sr.UnknownValueError:
        print("Sorry, could not understand the audio")
    except sr.RequestError:
        print("Could not request results; check your internet connection")

# Run the function
speech_to_text()
