import React, { useState, useEffect } from "react";
import { View, Text, ScrollView, Button, RefreshControl, TouchableOpacity } from "react-native";
import { getTicket, Ticket } from "../../lib/api";
import axios from "axios";
import { API_BASE } from "../../lib/api";

export default function TicketList({ userId }: { userId: string }) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);

  async function fetchTickets() {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/tickets?user_id=${userId}`);
      setTickets(res.data);
    } catch (e: any) {
      console.error("Fetch error", e?.message || e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchTickets();
  }, [userId]);

  return (
    <ScrollView
      style={{ flex: 1, padding: 16 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={fetchTickets} />}
    >
      <Text style={{ fontSize: 22, fontWeight: "600", marginBottom: 12 }}>
        My Tickets
      </Text>

      {tickets.length === 0 && !loading && (
        <Text style={{ color: "#666" }}>No tickets yet. Submit one to get started.</Text>
      )}

      {tickets.map((t) => (
        <TouchableOpacity
          key={t.id}
          style={{
            borderWidth: 1,
            borderColor: "#ddd",
            borderRadius: 8,
            padding: 12,
            marginBottom: 12,
          }}
          onPress={() => {
            // Example: open detail view or copy ID
            console.log("Ticket tapped:", t.id);
          }}
        >
          <Text style={{ fontWeight: "600" }}>{t.brand} – {t.category}</Text>
          <Text>Status: {t.status}</Text>
          <Text>ID: {t.id.slice(0, 8)}...</Text>
          <Text>Created: {new Date(t.created_at).toLocaleDateString()}</Text>
        </TouchableOpacity>
      ))}

      <Button title="Refresh" onPress={fetchTickets} />
    </ScrollView>
  );
}
