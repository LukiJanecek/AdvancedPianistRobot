Pro spuštení expo:
-Je třeba být v složce aplikace
  - pokud je to čerstvý commit.. je přeba dát ještě před zkuštením npm install
  - poté do terminálu dát: "npx expo start"


Je třeba stahnout aplikaci EXPO GO a naskenovat QR kod. Pokud máte android emulator na PC lze také využít. Je třeba být ve stejné síti s mobilem (školni síť nefunguje je třeba si vytvořit hotspot). 

Pro spuštění ve web je třeba doinstalovat balíček: "npx expo install react-dom react-native-web" do složky aplikace.


npx expo export -p web

npx expo export -p android