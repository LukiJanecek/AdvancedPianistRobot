import { StyleSheet, ScrollView, Pressable } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

export default function MainScreen() {

  const keys = Array.from({ length: 36 }, (_, i) => i + 1);

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Pianist page</ThemedText>
      <ThemedText style={styles.text}>Welcome to the Main Screen!</ThemedText>
      
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.keysRow}>
        {keys.map((key) => (
          <Pressable key={key} style={({ pressed }) => [styles.key, 
            { backgroundColor: pressed ? '#ccc' : '#fff' },]}
            onPress={() => console.log(`Key ${key} pressed`)}>
          
            <ThemedText style={styles.keyLabel}>{key}</ThemedText>
          </Pressable>))}
      </ScrollView>
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
  marginTop: 30,
  flexDirection: 'row',
  alignItems: 'center',
  },
  key: {
    width: 40,        // úzké tlačítko jako klávesa
    height: 120,
    marginHorizontal: 2,
    borderWidth: 1,
    borderColor: '#000',
    borderRadius: 4,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  keyLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
});