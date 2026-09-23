import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, SafeAreaView, Alert } from 'react-native';
import { AuthStorage } from '@/lib/auth';

export default function SettingsScreen() {
  const [tokenStatus, setTokenStatus] = useState<string>('Present (Hardware SecureStore)');

  const handleClearSession = async () => {
    await AuthStorage.deleteToken();
    setTokenStatus('Cleared');
    Alert.alert('Session Cleared', 'Your secure session tokens have been removed from the hardware keychain.');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Sovereignty Compliance Status */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>🇮🇳 Data Sovereignty & Region Lock</Text>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Execution Region:</Text>
            <Text style={styles.valueHighlight}>asia-south1 (Mumbai, India)</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Zero Data Retention:</Text>
            <Text style={styles.valueSuccess}>Active (Strict No-Cache)</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Database:</Text>
            <Text style={styles.value}>Cloud SQL PostgreSQL 16 (Private VPC)</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Data Principal Rights:</Text>
            <Text style={styles.value}>DPDP Act 2023 Compliant</Text>
          </View>
        </View>

        {/* Hardware Security */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>🔒 Device Hardware Security</Text>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Token Vault:</Text>
            <Text style={styles.value}>expo-secure-store</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Storage Status:</Text>
            <Text style={styles.valueSuccess}>{tokenStatus}</Text>
          </View>

          <TouchableOpacity style={styles.dangerButton} onPress={handleClearSession}>
            <Text style={styles.dangerButtonText}>Purge Hardware Keychain Session</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#090D16',
  },
  content: {
    padding: 16,
    gap: 16,
  },
  sectionCard: {
    backgroundColor: '#0F172A',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1E293B',
    gap: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#F8FAFC',
    marginBottom: 4,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    fontSize: 13,
    color: '#94A3B8',
  },
  value: {
    fontSize: 13,
    color: '#E2E8F0',
    fontWeight: '500',
  },
  valueHighlight: {
    fontSize: 13,
    color: '#38BDF8',
    fontWeight: '600',
  },
  valueSuccess: {
    fontSize: 13,
    color: '#34D399',
    fontWeight: '600',
  },
  dangerButton: {
    backgroundColor: '#7F1D1D',
    marginTop: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#EF4444',
  },
  dangerButtonText: {
    color: '#FEE2E2',
    fontWeight: '600',
    fontSize: 13,
  },
});
