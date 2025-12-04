//admin.tsx
import { StyleSheet, Pressable, View, Text } from 'react-native';
import { useColorScheme } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useState, useEffect } from 'react';
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

  useEffect(() => {
  if (!waiting) return;

  if (role === "performer") {
    setWaiting(false);
    router.navigate("/piano");
  }
  else {
    //alert("Již někdo hraje, počkejte prosím.");
  }


}, [role, waiting]);
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
          <ThemedText style={styles.btnText}>
            role: {role}
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

      <View style={{ marginTop: 120, gap: 12, width: "50%", paddingHorizontal: 20, height: 200}}>

        <Pressable
          onPress={async () => {
            try {
              if (role == "performer") {
                router.navigate("/piano");
              }
              if (role!=="performer") {
                const res = await requestPerformer();
                
                if (!res.ok) {
                  if (res.reason === "conflict") {
                    alert("Již někdo hraje. Počkejte prosím, až skončí.");
                  } else if (res.reason === "network") {
                    alert("Chyba připojení. Zkuste to prosím znovu.");
                  }
                  return;
                }
                
                setWaiting(true);
              }
            }catch (err: any) {
              console.error("failed:", err);
              alert("Něco se pokazilo. Zkuste to prosím znovu.");
            }
          }}
          style={({ pressed }) => ({
            padding: 12,
            borderRadius: 8,
            backgroundColor: pressed ? "#004f49ff" : "#00A499",
            alignItems: "center",
          })}
        >
          <Text style={styles.btnText}>
            Začít hrát
          </Text>
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
