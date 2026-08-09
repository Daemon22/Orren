// Orren-generated event handlers
'use strict';

// original_audio activates on always
document.getElementById('microphone-application-home-microphone-control').addEventListener('dblclick', () => {
  // activates: microphone_control on double_click
  console.log('activated: microphone_application.home.microphone_control');
});

/* BRIDGE: volume_down event not directly available in web; requires native shell or media-keys API. */
// microphone_control activates on volume_down × 2

// lifecycle for microphone_control: idle/active -> active/recording -> recording/processing -> processing/idle
