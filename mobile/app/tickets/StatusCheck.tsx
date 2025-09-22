import React, { useState } from "react";
import { View, Text, TextInput, Button, Alert, ScrollView } from "react-native";
import { getTicket, getResult, Ticket, Result } from "../../lib/api";

export default function StatusCheck() {
  const [ticketId, setTicketId] = useState("");
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchStatus() {
    if (!ticketId.trim()) {
      Alert.alert("Missing", "Enter a ticket ID.");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const t = await getTicket(ticketId.trim());
      setTicket(t);
      // Try result (may 404 if not resolved yet)
      try {
        const r = await getResult(ticketId.trim());
        setResult(r);
      } catch {
        setResult(null);
      }
    } catch (e: any) {
      setTicket(null);
      setResult(null);
      Alert.alert("Not found", e?.response?.data?.detail || "Ticket not found");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 22, fontWeight: "600" }}>Check Ticket Status</Text>

      <Text>Ticket ID</Text>
      <TextInput
        value={ticketId}
        onChangeText={setTicketId}
        placeholder="Paste your ticket ID"
        autoCapitalize="none"
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />
      <Button title={loading ? "Loading..." : "Check"} onPress={fetchStatus} disabled={loading} />

      {ticket && (
        <View style={{ borderWidth: 1, borderColor: "#ddd", padding: 12, borderRadius: 8 }}>
          <Text style={{ fontWeight: "600" }}>Ticket</Text>
          <Text>ID: {ticket.id}</Text>
          <Text>Status: {ticket.status}</Text>
          <Text>Brand: {ticket.brand}</Text>
          <Text>Category: {ticket.category}</Text>
          <Text>Created: {new Date(ticket.created_at).toLocaleString()}</Text>
          <Text>Updated: {new Date(ticket.updated_at).toLocaleString()}</Text>
        </View>
      )}

      {result && (
        <View style={{ borderWidth: 1, borderColor: "#ddd", padding: 12, borderRadius: 8 }}>
          <Text style={{ fontWeight: "600" }}>Result</Text>
          <Text>Verdict: {result.verdict}</Text>
          <Text>Rationale: {result.rationale || "—"}</Text>
          <Text>Reviewer: {result.reviewer_id || "—"}</Text>
          <Text>Reviewed at: {new Date(result.reviewed_at).toLocaleString()}</Text>
        </View>
      )}
    </ScrollView>
  );
}
