import { StyleSheet, Pressable, ScrollView, View, Text, ImageBackground } from 'react-native';
import { useColorScheme } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useState, useEffect } from 'react';
import { useIsFocused } from '@react-navigation/native';
import { useWs } from "./_layout";
import { useRobotConnectionPoller } from '@/hooks/useRobotConnectionPoller';
import BirthdayImg from '../../assets/images/Birthday.jpg';
import StarWarsImg from '../../assets/images/StarWars1.jpg';
import BeethovenImg from '../../assets/images/Beethoven.jpg';
import { router } from "expo-router";

export default function MainScreen() {
  const isFocused = useIsFocused();

  // robot connection status
  const { status, isLoading } = useRobotConnectionPoller(3000, isFocused);

  const colorScheme = useColorScheme();
  
  // websocket
  const { send, presence, role, state, canControl, events, robotState, releasePerformer } = useWs();

  // pro test si tam dej fake hodnoty:
  //const send = () => {};
  //const presence = null;
  //const role = "tester";
  //const state = "idle";
  //const canControl = false;
  
  const dotColor = isLoading ? "#F59E0B" : status.online ? "#22C55E" : "#EF4444";
  
  //const dotColor = "#22C55E";

  const label = isLoading ? "Kontrola připojení..." : status.online ? "Robot připojen" : "Robot odpojen";

  //const label = "Robot připojen";
  
  const [lastPressed, setLastPressed] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<any | null>(null);

  const [isReleasing, setIsReleasing] = useState(false);

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
      {/*<ThemedText style={styles.btnText}>
                  role: {role}
                </ThemedText>*/}
      <View style={{ gap: 4 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <View style={{
            width: 10, height: 10, borderRadius: 5, backgroundColor: dotColor
          }}/>
          
          <ThemedText style={{ fontSize: 16, fontWeight: "600", color: '#ffffff'}}>
            {label}
          </ThemedText>

          {/*<ThemedText style={{ opacity: 0.8}}>
            {isLoading
              ? "Kontroluji připojení…"
              : `Target: ${status.ip ?? "unknown"}${
                  status.port ? `:${status.port}` : ""
                }`}
          </ThemedText>*/}
        </View>
      </View>
      {/*<ThemedText style={styles.text}>
        WS: {state} • role: {role} • watchers: {presence?.watchers ?? '-'}
      </ThemedText>*/}
      
{/*
      {/*<View style={{ marginTop: 16, gap: 4 }}>
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
          </ThemedText>
        </View>
      </View>*/}
      {/*
      
      {role === 'undefined' && (
        <ThemedText style={styles.note}>Čekám na přiřazení role od serveru…</ThemedText>
      )}
      {role !== 'performer' && role !== 'undefined' && (
        <ThemedText style={styles.note}>Room už má performera — jsi watcher (ovládání vypnuto).</ThemedText>
      )}

      {status.playing_song && (
        <ThemedText style={{ marginTop: 8, opacity: 0.8 }}>
          Robot právě hraje - tlačítka jsou zamčená.
        </ThemedText>
      )}
      */}
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
      
      <ScrollView
          style={styles.keysScroller} 
          contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', alignItems: 'center' }}
          showsHorizontalScrollIndicator={false}>
      <View style={styles.buttonsRow}>
        {buttons.map((b) => {
          const isHappy = b.label === "Happy Birthday";
          const isStarWars = b.label === "Star wars";
          const isBeeth = b.label === "Beethoven";

          return (
            <Pressable
              key={b.id}
              disabled={!canControl || status.playing_song === true}
              onPress={() => onPressSong(b)}
              style={({ pressed }) => [
                styles.btn,
                isStarWars && styles.starWarsBtn,
                isHappy && styles.starWarsBtn,
                pressed && { opacity: 0.7 },
              ]}
            >
               {isHappy ? (
                <ImageBackground
                    source={BirthdayImg}
                     resizeMode="cover"
                       style={[
                       styles.starWarsBg,
                        status.playing_song && { opacity: 0.4 }
                        ]}
                         imageStyle={{ borderRadius: 10 }}
                          >
                         <Text style={[
                          styles.ButtonText,
                          //status.playing_song && { color: '#888888' }
                           ]}>Happy Birthday</Text>
                          </ImageBackground>
                           ) : (
                              null
                           )}
                         {isStarWars ? (
                <ImageBackground
                   source={StarWarsImg}
                    resizeMode="cover"
                    style={[
                    styles.starWarsBg,
                      status.playing_song && { opacity: 0.4 }
                    ]}
                       imageStyle={{ borderRadius: 10 }}
                          >
                       <Text style={[
                         styles.ButtonText,
                           //status.playing_song && { color: '#888888' }
                           ]}>STAR WARS</Text>
                        </ImageBackground>
                           ) : (
                               null
                                )}
                           {isBeeth ? (
                        <ImageBackground
                  source={BeethovenImg}
                       resizeMode="cover"
                          style={[
                        styles.starWarsBg,
                           status.playing_song && { opacity: 0.4 }
                              ]}
                          imageStyle={{ borderRadius: 10 }}
                            >
                          <Text style={[
                           styles.ButtonText,
                              //status.playing_song && { color: '#888888' }
                             ]}>Beethoven</Text>
                              </ImageBackground>
              ) : (
                null
              )}
            </Pressable>
            
            
          );
        })}
      </View>
      </ScrollView>

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
    backgroundColor: '#121212',
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
    width: '80%',
    maxWidth: 600,
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
  keysScroller: {
    width: '100%',
    height: '100%',
  },
  footerPayload: {
    marginTop: 6,
    fontSize: 12,
    color: '#6b7280',
  },
  starWarsBtn: {
    padding: 0,       // žádné vnitřní odsazení
    overflow: "hidden",
  },

  starWarsBg: {
    width: "100%",
    height: "100%",
    justifyContent: "center",
    alignItems: "center",
  },

  ButtonText: {
    fontSize: 26,
    fontWeight: "900",
    color: "#ffffffff",        // zlatá jako Star Wars
    textShadowColor: "#000000ff",
   // textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 10,
  },
});
