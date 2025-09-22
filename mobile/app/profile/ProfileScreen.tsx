import React from "react";
import { View, Text } from "react-native";

export default function ProfileScreen({ userId }: { userId: string }) {
  return (
    <View style={{ padding: 16, gap: 8 }}>
      <Text style={{ fontSize: 22, fontWeight: "600" }}>Profile</Text>
      <Text>User: {userId}</Text>
      {/* Add history, preferences, push-token, etc. later */}
    </View>
  );
}
