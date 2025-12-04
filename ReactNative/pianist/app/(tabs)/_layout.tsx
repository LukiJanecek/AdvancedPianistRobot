// app/(tabs)/_layout.tsx
import { Tabs } from "expo-router";
import { createContext, useContext, useRef } from "react";
import { Platform } from "react-native";

import { HapticTab } from "@/components/haptic-tab";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";
import { useIsFocused } from "@react-navigation/native";

import { useWebSocket } from "@/hooks/useWebSocket";
import { useState } from "react";
import { Modal, View, TextInput, Button, Text } from "react-native";
import { useNavigation } from "expo-router";
import { router } from "expo-router";
import { useEffect } from "react";
import { useSegments, useRouter } from "expo-router";




const WebSocketContext = createContext<ReturnType<typeof useWebSocket> | null>(null);

export const useWs = () => {
  const ctx = useContext(WebSocketContext);
  
  if (!ctx) throw new Error("useWs must be used inside provider");
  return ctx;
};



export const unstable_settings = { initialRouteName: "Main" };

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const isFocused = useIsFocused();
  const navigation = useNavigation();

  const [adminVisible, setAdminVisible] = useState(false);
  const [password, setPassword] = useState("");
  const correctPass = "1111"; // ← změň si podle sebe

  const handleAdminPress = () => {
    setAdminVisible(true);
  };

  const confirmPass = () => {
  if (password === correctPass) {
    setAdminVisible(false);
    setPassword("");

    router.navigate("/Admin");

  } else {
    alert("Špatné heslo");
  }
};

  // stabilní device id pro celou appku
  const deviceRef = useRef<string | null>(null);
  if (!deviceRef.current) {
    const platform = Platform.OS ?? "unknown";
    const rand = Math.random().toString(36).slice(2, 8);
    const ts = Date.now().toString(36);
    deviceRef.current = `${platform}-${rand}-${ts}`;
  }

  // jediná WS instance
  const ws = useWebSocket({ device: deviceRef.current, echoSelf: false, enabled: isFocused });

  const releasePerformer = ws?.releasePerformer ?? (() => {});

  

  const { role } = ws ?? {};

  if (role === undefined || role === null) {
  return null; // nebo loading
}

  ////////////

const segments = useSegments();
const router = useRouter();

useEffect(() => {
  if (!role) return;
  // Spojí segmenty do cesty, např. ["piano"] → "/piano"
  const current = "/" + segments.join("/");

  if (role === "undefined" || role === "watcher") {
    if ((current.includes("piano") || current.includes("songs"))){
    router.replace("/Main");
    }
  }
}, [role, segments]);

//////////////
  return (
    <WebSocketContext.Provider value={ws}>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: Colors[colorScheme ?? "light"].tint,
          headerShown: false,
          tabBarButton: HapticTab,
        }}
      >
        <Tabs.Screen
          name="Main"
          options={{
            title: "Main",
          }}
          listeners={{
    tabPress: (e) => {
      releasePerformer();
    },
  }}
        />
        <Tabs.Screen
          name="piano"
          options={{
            title: "Piano",
            tabBarIcon: ({ color }) => (
              <IconSymbol size={28} name="pianokeys" color={color} />
            ),
            href: role === "performer" ? "/piano" : null,
          }}
        />
        <Tabs.Screen
          name="songs"
          options={{
            title: "Skladby",
            tabBarIcon: ({ color }) => (
              <IconSymbol size={28} name="music.note.list" color={color} />
            ),
            href: role === "performer" ? "/songs" : null,
          }}
        />
        <Tabs.Screen
  name="Admin"
  options={{
    title: "Admin",
    tabBarIcon: ({ color }) => (
      <IconSymbol size={28} name="key" color={color} />
    ),
  }}
  listeners={{
    tabPress: (e) => {
      e.preventDefault();
      setAdminVisible(true);
    },
  }}
/>

        </Tabs>
         <Modal visible={adminVisible} transparent animationType="fade">
          <View
            style={{
              flex: 1,
              justifyContent: "center",
              alignItems: "center",
              backgroundColor: "rgba(0,0,0,0.5)",
            }}
          >
            <View
              style={{
                backgroundColor: "white",
                width: 280,
                padding: 20,
                borderRadius: 10,
              }}
            >
              <Text style={{ fontSize: 18, marginBottom: 10 }}>
                Zadejte admin heslo
              </Text>

              <TextInput
                secureTextEntry
                value={password}
                onChangeText={setPassword}
                style={{
                  borderWidth: 1,
                  borderColor: "#ccc",
                  borderRadius: 6,
                  padding: 10,
                  marginBottom: 12,
                }}
              />

              <Button title="Potvrdit" color="#00A499" onPress={confirmPass} />
              <Button
                title="Zrušit"
                color="#454545ff"
                onPress={() => setAdminVisible(false)}
              />
            </View>
          </View>
        </Modal>
      
      
    </WebSocketContext.Provider>
  );
}
