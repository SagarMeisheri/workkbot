import React, { useState } from 'react';
import { View, Text, Switch, StyleSheet, ScrollView, SafeAreaView } from 'react-native';

interface ConsentItem {
  id: string;
  type: string;
  title: string;
  description: string;
  granted: boolean;
  version: string;
}

export default function ConsentScreen() {
  const [consents, setConsents] = useState<ConsentItem[]>([
    {
      id: '1',
      type: 'CORE_CHAT',
      title: 'Core Conversational Assistant',
      description: 'Enables real-time sovereign chat and context handling strictly in Mumbai (asia-south1).',
      granted: true,
      version: 'v1.0.0',
    },
    {
      id: '2',
      type: 'WORKSPACE_INTEGRATION',
      title: 'Google Workspace Integration',
      description: 'Permits the assistant to query Gmail and Drive using temporary scoped OAuth tokens.',
      granted: false,
      version: 'v1.0.0',
    },
    {
      id: '3',
      type: 'ZOHO_INTEGRATION',
      title: 'Zoho CRM & Desk Integration',
      description: 'Permits searching leads and support tickets via Zoho Model Context Protocol (MCP).',
      granted: false,
      version: 'v1.0.0',
    },
  ]);

  const toggleConsent = (id: string) => {
    setConsents((prev) =>
      prev.map((c) => (c.id === id ? { ...c, granted: !c.granted } : c))
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerBox}>
          <Text style={styles.headerTitle}>DPDP Act 2023 Consent Ledger</Text>
          <Text style={styles.headerSubtitle}>
            Every consent change is cryptographically audited and recorded in Cloud SQL RLS.
          </Text>
        </View>

        {consents.map((item) => (
          <View key={item.id} style={styles.consentCard}>
            <View style={styles.cardHeader}>
              <View style={styles.titleGroup}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.versionBadge}>{item.version}</Text>
              </View>
              <Switch
                value={item.granted}
                onValueChange={() => toggleConsent(item.id)}
                trackColor={{ false: '#334155', true: '#0284C7' }}
                thumbColor={item.granted ? '#38BDF8' : '#94A3B8'}
              />
            </View>
            <Text style={styles.cardDesc}>{item.description}</Text>
            <Text style={styles.statusText}>
              Status: {item.granted ? '✅ GRANTED' : '❌ REVOKED'}
            </Text>
          </View>
        ))}
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
  headerBox: {
    backgroundColor: '#0F172A',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1E293B',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#F8FAFC',
    marginBottom: 6,
  },
  headerSubtitle: {
    fontSize: 13,
    color: '#94A3B8',
    lineHeight: 18,
  },
  consentCard: {
    backgroundColor: '#0F172A',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1E293B',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  titleGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#FFFFFF',
    flexShrink: 1,
  },
  versionBadge: {
    fontSize: 11,
    color: '#38BDF8',
    backgroundColor: '#0F2942',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  cardDesc: {
    fontSize: 13,
    color: '#94A3B8',
    lineHeight: 18,
    marginBottom: 10,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#CBD5E1',
  },
});
