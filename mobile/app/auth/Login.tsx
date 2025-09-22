import React, { useState } from "react";
import { View, Text, TextInput, Button, Alert } from "react-native";

/** Placeholder only — no real auth yet */
export default function Login({ onLogin }: { onLogin: (userId: string) => void }) {
  const [userId, setUserId] = useState("kev");

  function handleLogin() {
    if (!userId.trim()) return Alert.alert("Missing", "Enter a user id");
    onLogin(userId.trim());
  }

  return (
    <View style={{ padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 22, fontWeight: "600" }}>Login (placeholder)</Text>
      <Text>User ID</Text>
      <TextInput
        value={userId}
        onChangeText={setUserId}
        placeholder="e.g., kev"
        autoCapitalize="none"
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />
      <Button title="Continue" onPress={handleLogin} />
    </View>
  );
}
