//admin.tsx
import { StyleSheet, Pressable, View, Text, ActivityIndicator } from 'react-native';
import { useColorScheme } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useState, useEffect, useRef } from 'react';
import { useIsFocused } from '@react-navigation/native';
import { apiGet, apiPost } from '@/utils/api';
import { useWs } from "./_layout";
import { useRobotConnectionPoller } from '@/hooks/useRobotConnectionPoller';
import { ROOM } from "../../constants/config";
import { useNavigation } from "expo-router";
import { router } from "expo-router";
import { Tabs } from "expo-router";


export default function MainScreen() {
  const isFocused = useIsFocused();
  const { requestPerformer } = useWs();

  // robot connection status
  const { status, isLoading } = useRobotConnectionPoller(3000, isFocused);


  const colorScheme = useColorScheme();
  
  // websocket
  const { send, presence, role, state, canControl, events, robotState, clientId: selfClientId } = useWs();

  
  const dotColor = isLoading ? "#F59E0B" : status.online ? "#22C55E" : "#EF4444";
  
  //const dotColor = "#22C55E";

  const label = isLoading ? "Kontrola připojení..." : status.online ? "Robot připojen" : "Robot odpojen";

  //const label = "Robot připojen";


  
  const [lastPressed, setLastPressed] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<any | null>(null);


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

const [waiting, setWaiting] = useState(false);

// Track last request time to prevent rapid requests
const lastRequestTimeRef = useRef<number>(0);
const isRequestingRef = useRef(false);

useEffect(() => {
  if (!waiting) return;

  if (role === "performer") {
    setWaiting(false);
    // Use replace to ensure clean navigation
    router.replace("/piano");
  }
}, [role, waiting]);

const handleRequestPerformer = async () => {
  const now = Date.now();
  
  // Debounce: prevent multiple rapid requests (1 second cooldown)
  if (now - lastRequestTimeRef.current < 1000) {
    console.log("Request debounced - too soon");
    return;
  }
  
  // Prevent concurrent requests
  if (isRequestingRef.current) {
    console.log("Request already in progress");
    return;
  }
  
  // Already a performer
  if (role === "performer") {
    router.replace("/piano");
    return;
  }
  
  try {
    isRequestingRef.current = true;
    lastRequestTimeRef.current = now;
    setWaiting(true);
    
    const result = await requestPerformer();
    
    if (result.ok) {
      console.log("Performer role granted");
      // Wait for role update via WebSocket
      // The useEffect above will handle navigation
    } else if (result.reason === "conflict") {
      setWaiting(false);
      alert("Již někdo hraje, počkejte prosím.");
    } else {
      setWaiting(false);
      alert("Nepodařilo se získat roli performera. Zkuste to prosím znovu.");
    }
  } catch (err) {
    console.error("Error requesting performer:", err);
    setWaiting(false);
    alert("Chyba při žádosti o roli performera.");
  } finally {
    isRequestingRef.current = false;
  }
};

  return (
    <ThemedView style={styles.container}>
      {/*<ThemedText type="title">Admin ovládání</ThemedText>*/}

      <View style={{ marginTop: 16, gap: 4 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <View style={{
            width: 10, height: 10, borderRadius: 5, backgroundColor: dotColor
          }}/>
          
          <ThemedText style={styles.btnText}>
            {label}
          </ThemedText>
          {/*<ThemedText style={styles.btnText}>
            role: {role}
          </ThemedText>*/}

          {/*<ThemedText style={{ opacity: 0.8 }}>
            {isLoading
              ? "Kontroluji připojení…"
              : `Target: ${status.ip ?? "unknown"}${
                  status.port ? `:${status.port}` : ""
                }`}
          </ThemedText>*/}
        </View>
        </View>

      <View style={{ marginTop: 120, gap: 12, width: "50%", paddingHorizontal: 20, height: 200}}>

        <Pressable
  disabled={waiting || role === "performer" || !status.shadow_start}
  onPress={handleRequestPerformer}
  style={({ pressed }) => ({
    padding: 16,
    borderRadius: 8,
    backgroundColor: waiting 
      ? "#888" 
      : role === "performer"
      ? "#4CAF50"
      : pressed 
      ? "#004f49ff" 
      : "#00A499",
    alignItems: "center",
    opacity: waiting ? 0.6 : 1,
  })}
>
  {waiting ? (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <ActivityIndicator color="white" size="small" />
      <Text style={styles.btnText}>Čekám na roli...</Text>
    </View>
  ) : (
    <Text style={styles.btnText}>
      {role === "performer" ? "Jste performer" : "Začít hrát"}
    </Text>
  )}
</Pressable>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 24,
    alignItems: 'center',
    backgroundColor: '#121212',
  },
  text: {
    marginTop: 8,
    fontSize: 14,
    textAlign: 'center',
    
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
