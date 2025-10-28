import { StyleSheet, Pressable, View, Text } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useState, useEffect } from 'react';

import { apiPost } from '@/utils/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useRobotConnectionPoller } from '@/hooks/useRobotConnectionPoller';

export default function MainScreen() {
  
  // websocket
  const { send, presence, role, state, canControl } = useWebSocket(Date.now().toString());

  // robot connection status
    const { status, isLoading } = useRobotConnectionPoller();
    const dotColor = status.online ? "#22C55E" : "#EF4444";
    const label = isLoading
      ? "Checking robot..."
      : status.online
        ? "Robot connected"
        : "Robot disconnected";

  const [lastPressed, setLastPressed] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<any | null>(null);

  const buttons = [
    { id: 1, label: 'Lehká' },
    { id: 2, label: 'Střední' },
    { id: 3, label: 'Těžká' },
  ];

  const onPressSong = async (btn: { id: number; label: string }) => {
    if (!canControl) {
      return;
    }
    const ts = Date.now();
    const payload = { type: 'song_button', button: btn.id, label: btn.label, ts };
    send(payload);

    try {
      const result = await apiPost('/robot/playSong', {
        songId: btn.id 
      });
      console.log('API response:', result);
    } 
    catch (err) {
      console.error('API error:', err);
    }

    setLastPressed(`${btn.label} pressed`);
    setLastPayload(payload);
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Songs</ThemedText>
      <ThemedText style={styles.text}>Zvol si svou písničku a odešli na KUKA robota.</ThemedText>
      <ThemedText style={styles.text}>
        WS: {state} • role: {role} • watchers: {presence?.watchers ?? '-'}
      </ThemedText>

      <View style={{ gap: 4 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <View style={{
            width: 10, height: 10, borderRadius: 5, backgroundColor: dotColor
          }}/>
          <Text style={{ fontSize: 16, fontWeight: "600" }}>{label}</Text>
          {!isLoading && status.online && status.latency_ms != null && (
            <Text style={{ marginLeft: 8 }}>({status.latency_ms} ms)</Text>
          )}
          {!isLoading && !status.online && status.error && (
            <Text style={{ marginLeft: 8, opacity: 0.7 }}>[{status.error}]</Text>
          )}
        </View>

        {!isLoading && (
          <Text style={{ opacity: 0.8 }}>
            Target: {status.ip ?? "unknown"}{status.port ? `:${status.port}` : ""}
          </Text>
        )}
      </View>

      {role === 'undefined' && (
        <ThemedText style={styles.note}>Čekám na přiřazení role od serveru…</ThemedText>
      )}
      {role !== 'performer' && role !== 'undefined' && (
        <ThemedText style={styles.note}>Room už má performera — jsi watcher (ovládání vypnuto).</ThemedText>
      )}

      <View style={styles.buttonsRow}>
        {buttons.map((b) => (
          <Pressable
            key={b.id}
            disabled={!canControl}
            onPress={() => onPressSong(b)}
            style={({ pressed }) => [
              styles.btn,
              pressed ? styles.btnPressed : null,
              !canControl ? styles.btnDisabled : null,
            ]}
          >
            <ThemedText style={styles.btnText}>{b.label}</ThemedText>
          </Pressable>
        ))}
      </View>

      <View style={styles.footer}>
        <ThemedText style={styles.footerText}>
          {lastPressed ? lastPressed : 'Ještě nic nebylo stisknuto'}
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
    paddingTop: 24,
    alignItems: 'center',
  },
  text: {
    marginTop: 8,
    fontSize: 14,
    textAlign: 'center',
  },
  note: {
    marginTop: 6,
    fontSize: 13,
    textAlign: 'center',
    opacity: 0.8,
  },
  buttonsRow: {
    marginTop: 28,
    width: '100%',
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
  btnPressed: {
    backgroundColor: '#f3f4f6',
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnText: {
    fontSize: 16,
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
