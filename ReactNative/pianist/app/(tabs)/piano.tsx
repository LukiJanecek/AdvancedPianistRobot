//piano.tsx
import { StyleSheet, ScrollView, View, Text } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useState, useRef, useEffect } from 'react';
import { useColorScheme } from 'react-native';
import { useIsFocused } from '@react-navigation/native';
import { apiGet, apiPost } from '@/utils/api';
import { useRobotConnectionPoller } from '@/hooks/useRobotConnectionPoller';
import { useWs } from "./_layout";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { ROOM } from "../../constants/config";
import { router } from "expo-router";
import { Platform } from "react-native";
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { Pressable } from 'react-native-gesture-handler';



export default function MainScreen() {
  const isFocused = useIsFocused();

  // robot connection status
  const { status, isLoading } = useRobotConnectionPoller(3000, isFocused);

  const deviceRef = useRef<string | null>(null);
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';

  // websocket
  const { send, presence, role, state, canControl, events, robotState, clientId: selfClientId, releasePerformer } = useWs();

  //const { send, canControl, role, requestPerformer } = useWs(); // Toto je nova

  const dotColor = isLoading ? "#F59E0B" : status.online ? "#22C55E" : "#EF4444";
  
  //const dotColor = "#22C55E";

  const label = isLoading ? "Kontrola připojení..." : status.online ? "Robot připojen" : "Robot odpojen";

  //const label = "Robot připojen";

  
  // keys
  const keys = Array.from({ length: 22 }, (_, i) => i + 1);
  const blackKeyPositions = [1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 18, 19, 20]; 
  const [lastPressed, setLastPressed] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<any | null>(null);

  const [isReleasing, setIsReleasing] = useState(false);

  const whiteKeyDownTs = useRef<{ [key: number]: number }>({});
  const blackKeyDownTs = useRef<{ [key: number]: number }>({});

  const [pressedKeys, setPressedKeys] = useState<{ [key: string]: boolean }>({});

  // Add this state declaration near the top with your other state declarations
const [dissablebutton, setDissablebutton] = useState(false);

// Add this useEffect to update the button state based on status
useEffect(() => {
  if (!status.in_shadow_mode && !status.shadow_auto_stopped) {
    setDissablebutton(true);
  } else {
    setDissablebutton(false);
  }
}, [status.in_shadow_mode, status.shadow_auto_stopped]);

  

  // 1) Reakce na events – jen vizuální stav kláves
  useEffect(() => {
    if (!events.length) return;
    const last = events[events.length - 1] as any;
    
    if (
      (last.type === "note_on" || last.type === "note_off") &&
      typeof last.note !== "undefined"
    ) {
      if (last.type === "note_on") {
        setPressedKeys(prev => ({ ...prev, [last.note]: true }));
      }
      if (last.type === "note_off") {
        setPressedKeys(prev => {
          const updated = { ...prev };
          delete updated[last.note];
          return updated;
        });
      }
    }
  }, [events]);

  useEffect(() => {
    if (!canControl || !status.online || !isFocused) {
      return;
    }

    let cancelled = false;

    const startShadowing = async () => {
      try {
        const result = await apiPost("/Kuka/startShadowing", {});
        if (!cancelled) {
          console.log("Shadowing started:", result);
        }
      } catch (err: any) {
        if (!cancelled) {
          console.error("Start shadowing failed:", err);
        }
      }
    };

    const stopShadowing = async () => {
      try {
        const result = await apiPost("/Kuka/stopShadowing", {});
        console.log("Shadowing stopped:", result);
      } catch (err: any) {
        console.error("Stop shadowing failed:", err.message);
      }
    };

    if (role == "performer"){
      startShadowing();
    }
    

    return () => {
      if (role == "performer"){
        cancelled = true;
        stopShadowing();
      }
    };

  }, [canControl, status.online, isFocused]); 


  
  const WHITE_W = 64; 
  const BLACK_W = 40;
  const WRAP_MARGIN = 3;
  const BLACK_BASE_LEFT = WHITE_W - BLACK_W / 2; // střed nad hranou bílé (≈44)
  const BLACK_TUNE_RIGHT = 20;                    
  //const BLACK_LEFT = BLACK_BASE_LEFT + BLACK_TUNE_RIGHT;
  const BLACK_LEFT = WHITE_W - BLACK_W / 2 + WRAP_MARGIN;

  const onWhitePressIn = (k: number) => {
    if (!canControl) return;
    const ts = Date.now();
    whiteKeyDownTs.current[k] = ts;
    const payloadOn = { type: "note_on", note: k, vel: 100, ts };
    setLastPressed(`White key ${k} pressed`);
    setLastPayload(payloadOn);
    send(payloadOn);
  };

  const onWhitePressOut = (k: number) => {
    if (!canControl) return;
    const tsUp = Date.now();
    const tsDown = whiteKeyDownTs.current[k];
    const duration = tsDown ? tsUp - tsDown : undefined;
    const payloadOff = { type: "note_off", note: k, ts: tsUp, duration };
    setLastPayload(payloadOff);
    send(payloadOff);
    delete whiteKeyDownTs.current[k];
  };

  const onBlackPressIn = (k: number) => {
    if (!canControl) return;
    const ts = Date.now();
    blackKeyDownTs.current[k] = ts;
    const payloadOn = { type: "note_on", note: `${k}#`, vel: 100, ts };
    setLastPressed(`Black key ${k}# pressed`);
    setLastPayload(payloadOn);
    //send(payloadOn);
  };

  const onBlackPressOut = (k: number) => {
    if (!canControl) return;
    const tsUp = Date.now();
    const tsDown = blackKeyDownTs.current[k];
    const duration = tsDown ? tsUp - tsDown : undefined;
    const payloadOff = { type: "note_off", note: `${k}#`, ts: tsUp, duration };
    setLastPayload(payloadOff);
    //send(payloadOff);
    delete blackKeyDownTs.current[k];
  };


  return (
    <ThemedView style={styles.container}>
      {/*<ThemedText style={styles.btnText}>
                  role: {role}
                </ThemedText>
     {/*<ThemedText type="title">Piano</ThemedText>*/}
     {/*<ThemedText style={styles.text}>Press any key and play on KUKA robot.</ThemedText>
      <ThemedText style={styles.text}>
        
        WS: {state} • role: {role} • watchers: {presence?.watchers ?? "-"}
        
      </ThemedText>
      
      {role === "undefined" && (
        <ThemedText style={{ marginTop: 6, fontSize: 14 }}>
          Čekám na přiřazení role od serveru...
        </ThemedText>
      )}
      {role !== "performer" && role !== "undefined" && (
        <ThemedText style={{ marginTop: 6, fontSize: 14 }}>
          Ovládání: Zakázáno
        </ThemedText>
      )}
      */}
      <View style={{ gap: 4 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <View style={{
            width: 10, height: 10, borderRadius: 5, backgroundColor: dotColor
          }}/>
          
          <ThemedText style={{ fontSize: 16, fontWeight: "600",color: '#ffffff' }}>
            {label}
          </ThemedText>

         {/* <ThemedText style={{ opacity: 0.8}}>
            {isLoading
              ? "Kontroluji připojení…"
              : `Target: ${status.ip ?? "unknown"}${
                  status.port ? `:${status.port}` : ""
                }`}
          </ThemedText>*/}
        </View>
      </View>

      <View style={{ paddingTop: 10}}>
        <Pressable
          disabled={isReleasing}
          onPress={async () => {
            if (isReleasing) return;
            
            try {
              setIsReleasing(true);
              await releasePerformer();
              await new Promise(resolve => setTimeout(resolve, 300));
              router.replace("/Main");
            } catch (err: any) {
              console.error("Release performer failed:", err);
            } finally {
              setIsReleasing(false);
            }
          }}
          style={({ pressed }) => ({
            padding: 12,
            borderRadius: 8,
            backgroundColor: isReleasing ? "#888" : (pressed ? "#004f49ff" : "#00A499"),
            alignItems: "center",
            opacity: isReleasing ? 0.6 : 1,
          })}
        >
          <Text style={styles.btnText}>
            {isReleasing ? "Uvolňuji..." : "Ukončit hraní"}
          </Text>
        </Pressable>
        </View>

      <View style={styles.keysWrap}>
        <ScrollView 
          horizontal 
          style={styles.keysScroller} 
          //contentContainerStyle={[styles.keysRow, { paddingBottom: 12 }]}
          showsHorizontalScrollIndicator={false}
          //contentContainerStyle={styles.keysRow}
          contentContainerStyle={[styles.keysRow, { flexGrow: 1 }]}
          //persistentScrollbar={true}        // Android: lišta zůstává viditelnější
          //indicatorStyle="black"            // iOS: styl indikátoru („black“/„white“/„default“)
          //scrollIndicatorInsets={{ bottom: -6 }} // iOS: mírné odsazení indikátoru
        > 
        {keys.map((key) => (
              <View key={`white-${key}`} style={styles.whiteKeyWrap}>
                <Pressable
                //  disabled={!canControl}
                  disabled={dissablebutton}
                  onPressIn={() => onWhitePressIn(key)}
                  onPressOut={() => onWhitePressOut(key)}
                  onLongPress={() => true}
                  delayLongPress={999999}
                  android_ripple={null}                      // android
                  android_disableSound={true}
                  style={({ pressed }) => [
                    styles.whiteKey,
                    {
                      borderColor:'#9ca3af',
                      backgroundColor:
                        pressed || pressedKeys[key]
                          ? (isDark ? '#e5e7eb' : '#ddd')
                          : '#ffffff',
                    },
                  ]}
                >
                  {/*<ThemedText style={styles.keyLabel}>{key}</ThemedText>*/}
                </Pressable>

                {blackKeyPositions.includes(key) && (
                  <Pressable
                    disabled={!canControl}
                    style={({ pressed }) => [
                      styles.blackKey,
                      {
                        backgroundColor:
                          pressed || pressedKeys[`${key}#`]
                            ? '#4b5563'
                            : '#000000',
                        left: BLACK_LEFT,
                      },
                    ]}
                    onPressIn={() => onBlackPressIn(key)}
                    onPressOut={() => onBlackPressOut(key)}
                  >
                    {/*<ThemedText style={styles.blackKeyLabel}>
                      {key}#
                    </ThemedText>*/}
                  </Pressable>
                )}
              </View>
            ))}
        </ScrollView>
       </View> 

      {/*<View
        style={[
          styles.footer,
          { borderColor: isDark ? '#374151' : '#e5e7eb' },
        ]}
      >
        {/*<ThemedText
          style={[
            styles.footerText,
            { color: isDark ? '#e5e7eb' : '#374151' },
          ]}
        >
          {lastPressed ? lastPressed : 'No key pressed yet'}
        </ThemedText>
        {lastPayload && (
          <ThemedText
            style={[
              styles.footerPayload,
              { color: isDark ? '#9ca3af' : '#6b7280' },
            ]}
          >
            {JSON.stringify(lastPayload, null, 2)}
          </ThemedText>
        )}
      </View>*/}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#121212',
  },
  text: {
   // marginTop: 20,
    fontSize: 16,
    textAlign: 'center',
  },
  keysRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    height: 200,       
    paddingHorizontal: 12,
  },
  whiteKeyWrap: {
    position: 'relative',
    marginHorizontal: 3,
  },
  whiteKey: {
    width: 64,        // úzké tlačítko jako klávesa
    height: 200,
    //marginHorizontal: 3,
    borderWidth: 1,
    borderColor: '#000',
    borderRadius: 6,
    justifyContent: 'flex-end',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 2,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
  blackKey: {
    position: 'absolute',
    top: 0,
    //left: 40, // trochu doprava, aby seděla nad mezerou
    width: 40,
    height: 110,
    borderRadius: 4,
    zIndex: 10,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  blackKeyLabel: {
    color: '#fff',
    fontSize: 12,
  },
  keyLabel: {
    fontSize: 12,
  },
  keysWrap: {
    marginTop: 24,
    width: '100%',
    height: 200,
  },
  keysScroller: {
    width: '100%',
    height: '100%',
  },
  footer: {
    borderColor: '#e5e7eb',
    width: '100%',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 14,
    color: '#374151',
  },
  footerPayload: {
    fontSize: 12,
    color: "#6b7280", // šedá
  },


  logoContainer: {
  position: 'absolute',
  top: 20,
  right: 20,
  zIndex: 999,       // stays above everything
},

logo: {
  width: 50,
  height: 50,
},
btnText: {
    fontSize: 20,
    color: '#ffffffff',
  },

});