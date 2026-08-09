// Orren-generated Swift (iOS)
// Target: native_shell (Swift)
// Application: microphone_application

import UIKit
import AVFoundation

class MicrophoneApplication: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.0, green: 0.5, blue: 0.3, alpha: 1.0)
        setupUI()
    }

    func setupUI() {
        let microphone_control = UIView()
        microphone_control.accessibilityIdentifier = "microphone_application.home.microphone_control"
        microphone_control.backgroundColor = UIColor(red: 0.180, green: 0.800, blue: 0.443, alpha: 1.0)
        view.addSubview(microphone_control)
    }

    private var audioEngine = AVAudioEngine()

    func activateMicrophone() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.record)
        try? session.setActive(true)
        let inputNode = audioEngine.inputNode
        // Recording tap installed
        try? audioEngine.start()
    }
}
