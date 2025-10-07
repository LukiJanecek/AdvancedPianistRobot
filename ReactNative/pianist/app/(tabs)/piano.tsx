import { StyleSheet, ScrollView, Pressable, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useState, useRef, useEffect } from 'react';

import { useWebSocket } from '@/hooks/useWebSocket';

export default function MainScreen() {

  const { send, presence, role, state, canControl, events } = useWebSocket(Date.now().toString());
  
  const keys = Array.from({ length: 36 }, (_, i) => i + 1);
  const blackKeyPositions = [1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 18, 19, 20, 22, 23, 25, 26, 27, 29, 30, 32, 33, 34]; // 25 black keys 
  const [lastPressed, setLastPressed] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<any | null>(null);

  const whiteKeyDownTs = useRef<{ [key: number]: number }>({});
  const blackKeyDownTs = useRef<{ [key: number]: number }>({});

    // --- Nové: stav pro zmáčknuté klávesy podle příchozích zpráv
  const [pressedKeys, setPressedKeys] = useState<{ [key: string]: boolean }>({});

useEffect(() => {
  if (!events.length) return;
  const last = events[events.length - 1];
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


  const WHITE_W = 64; 
  const BLACK_W = 40;
  const WRAP_MARGIN = 3;
  const BLACK_BASE_LEFT = WHITE_W - BLACK_W / 2; // střed nad hranou bílé (≈44)
  const BLACK_TUNE_RIGHT = 20;                    // tvé „posunout doprava o ~20“
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
    send(payloadOn);
  };

  const onBlackPressOut = (k: number) => {
    if (!canControl) return;
    const tsUp = Date.now();
    const tsDown = blackKeyDownTs.current[k];
    const duration = tsDown ? tsUp - tsDown : undefined;
    const payloadOff = { type: "note_off", note: `${k}#`, ts: tsUp, duration };
    setLastPayload(payloadOff);
    send(payloadOff);
    delete blackKeyDownTs.current[k];
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Pianist page</ThemedText>
      <ThemedText style={styles.text}>Press any key and play on KUKA robot.</ThemedText>
      <ThemedText style={styles.text}>
        WS: {state} • role: {role} • watchers: {presence?.watchers ?? "-"}
      </ThemedText>
      {role !== "performer" && (
        <ThemedText style={{ marginTop: 6, fontSize: 14 }}>
          Room už má performera — Jsi watcher (ovládání vypnuto).
        </ThemedText>
      )}
      <View style={styles.keysWrap}>
        <ScrollView 
          horizontal 
          style={styles.keysScroller} 
          //contentContainerStyle={[styles.keysRow, { paddingBottom: 12 }]}
          showsHorizontalScrollIndicator={true}
          //persistentScrollbar={true}        // Android: lišta zůstává viditelnější
          //indicatorStyle="black"            // iOS: styl indikátoru („black“/„white“/„default“)
          //scrollIndicatorInsets={{ bottom: 4 }} // iOS: mírné odsazení indikátoru
        > 
          <View style={styles.keysRow}>
            {keys.map((key) => (
              <View key={`white-${key}`} style={styles.whiteKeyWrap}>
                <Pressable
                  disabled={!canControl}
                  style={({ pressed }) => [
                    styles.whiteKey,
                    { backgroundColor: pressed || pressedKeys[key] ? '#ddd' : '#fff' },
                  ]}
                  onPressIn={() => onWhitePressIn(key)}
                  onPressOut={() => onWhitePressOut(key)}
                >
                  <ThemedText style={styles.keyLabel}>{key}</ThemedText>
                </Pressable>

                {/* Black keys  */}
                {blackKeyPositions.includes(key) && (
                  <Pressable
                    disabled={!canControl}
                    style={({ pressed }) => [
                      styles.blackKey,
                      { backgroundColor: pressed || pressedKeys[`${key}#`] ? '#444' : '#000', left: BLACK_LEFT },
                    ]}
                    onPressIn={() => onBlackPressIn(key)}
                    onPressOut={() => onBlackPressOut(key)}
                  >
                    <ThemedText style={styles.blackKeyLabel}>
                      {key}#
                    </ThemedText>
                  </Pressable>
                )}
              </View>
            ))}
          </View> 
        </ScrollView>
      </View>

      <View style={styles.footer}>
        <ThemedText style={styles.footerText}>
          {lastPressed ? lastPressed : 'No key pressed yet'}
        </ThemedText>
        {lastPayload && (
          <ThemedText style={styles.footerPayload}>
            {JSON.stringify(lastPayload, null, 2)}
          </ThemedText>
        )}
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    marginTop: 20,
    fontSize: 16,
    textAlign: 'center',
  },
  keysRow: {
    //marginTop: 30,
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 180,       
    paddingHorizontal: 12,
  },
  whiteKeyWrap: {
    position: 'relative',
    marginHorizontal: 3,
  },
  whiteKey: {
    width: 64,        // úzké tlačítko jako klávesa
    height: 180,
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
    marginBottom: 4,
    fontSize: 12,
  },
  keyLabel: {
    fontSize: 12,
    marginBottom: 4,
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
    marginTop: 32,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderColor: '#e5e7eb',
    width: '100%',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 14,
    color: '#374151',
  },
  footerPayload: {
    marginTop: 6,
    fontSize: 12,
    color: "#6b7280", // šedá
  },
});