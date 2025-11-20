//songs.tsx
import { StyleSheet, Pressable, View, Text } from 'react-native';
import { useColorScheme } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useState, useEffect } from 'react';
import { useIsFocused } from '@react-navigation/native';


import { useWs } from "./_layout";
import { useRobotConnectionPoller } from '@/hooks/useRobotConnectionPoller';

export default function MainScreen() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  
  // websocket
  const { send, presence, role, state, canControl, events, robotState } = useWs();

  // pro test si tam dej fake hodnoty:
  //const send = () => {};
  //const presence = null;
  //const role = "tester";
  //const state = "idle";
  //const canControl = false;

  // robot connection status
  const { status, isLoading } = useRobotConnectionPoller();
  
  const dotColor = isLoading
  ? "#F59E0B"        
  : status.online
  ? "#22C55E"         
  : "#EF4444";     

  const label = isLoading
    ? "Kontrola připojení..."
    : status.online
    ? "Robot připojen"
    : "Robot odpojen";
  
  const [lastPressed, setLastPressed] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<any | null>(null);

  const buttons = [
    { id: 1, label: 'Happy Birthday' },
    { id: 2, label: 'Star wars' },
    { id: 3, label: 'Beethoven' },
  ];

  const onPressSong = async (btn: { id: number; label: string }) => {
    
    if (!canControl) {
      return;
    }
    
    const ts = Date.now();
    const payload = { type: 'song_button', button: btn.id, label: btn.label, ts };
    send(payload);

    setLastPressed(`${btn.label} pressed`);
    setLastPayload(payload);
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Zahrej skladbu</ThemedText>
      {/*<ThemedText style={styles.text}>
        Zvol si svou písničku a odešli na KUKA robota.
      </ThemedText>*/}

     {/* <ThemedText style={styles.text}>
        WS: {state} • role: {role} • watchers: {presence?.watchers ?? '-'}
      </ThemedText>*/}

      <View style={{ marginTop: 16, gap: 4 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <View style={{
            width: 10, height: 10, borderRadius: 5, backgroundColor: dotColor
          }}/>
          
          <ThemedText style={{ fontSize: 16, fontWeight: "600" }}>
            {label}
          </ThemedText>

          {/*<ThemedText style={{ opacity: 0.8 }}>
            {isLoading
              ? "Kontroluji připojení…"
              : `Target: ${status.ip ?? "unknown"}${
                  status.port ? `:${status.port}` : ""
                }`}
          </ThemedText>*/}
        </View>
      </View>
      
      {/*{role === 'undefined' && (
        <ThemedText style={styles.note}>Čekám na přiřazení role od serveru…</ThemedText>
      )}*/}
      {role !== 'performer' && role !== 'undefined' && (
        <ThemedText style={styles.note}>Room už má performera — jsi watcher (ovládání vypnuto).</ThemedText>
      )}

      {status.playing_song && (
        <ThemedText style={{ marginTop: 8, opacity: 0.8 }}>
          Robot právě hraje - tlačítka jsou zamčená.
        </ThemedText>
      )}
      
      <View style={styles.buttonsRow}>
        {buttons.map((b) => (
          <Pressable
            key={b.id}
            disabled={!canControl || status.playing_song === true}
            onPress={() => onPressSong(b)}
            style={({ pressed }) => {
              const baseBg = isDark ? '#00A499' : '#ffffff';
              const pressedBg = isDark ? '#9b9b9bff' : '#f3f4f6';
              const border = isDark ? '#374151' : '#e5e7eb';

              return [
                styles.btn,
                {
                  backgroundColor: pressed ? pressedBg : baseBg,
                  borderColor: baseBg,
                },
                !canControl && styles.btnDisabled,
              ];
            }}
          >
            <ThemedText style={styles.btnText}>{b.label}</ThemedText>
          </Pressable>
        ))}
      </View>

      {/*<View
        style={[
          styles.footer,
          { borderColor: isDark ? '#374151' : '#e5e7eb' },
        ]}
      >
        <ThemedText
          style={[
            styles.footerText,
            { color: isDark ? '#e5e7eb' : '#374151' },
          ]}
        >
          {lastPressed ? lastPressed : 'Ještě nic nebylo stisknuto'}
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
    paddingTop: 24,
    alignItems: 'center',
  },
  text: {
    marginTop: 8,
    fontSize: 14,
    textAlign: 'center',
    color: '#ffffffff',
  },
  note: {
    marginTop: 6,
    fontSize: 13,
    textAlign: 'center',
    opacity: 0.8,
    color: '#ffffffff',
  },
  buttonsRow: {
    marginTop: 28,
    width: '50%',
    height: 200,
    paddingHorizontal: 16,
    gap: 12,
  },
  btn: {
    height: 56,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ffffff',
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnText: {
    fontSize: 20,
    color: '#ffffffff',
  },
  footer: {
    marginTop: 24,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderColor: '#e5e7eb',
    width: '100%',
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  footerText: {
    fontSize: 14,
    color: '#374151',
  },
  footerPayload: {
    marginTop: 6,
    fontSize: 12,
    color: '#6b7280',
  },
});
