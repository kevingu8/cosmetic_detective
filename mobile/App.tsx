import React, { useState } from "react";
import { SafeAreaView, StatusBar, Platform, View, Button } from "react-native";
import SubmitTicket from "./app/tickets/SubmitTicket";
import StatusCheck from "./app/tickets/StatusCheck";
import TicketList from "./app/tickets/TicketList";
import Login from "./app/auth/Login";
import ProfileScreen from "./app/profile/ProfileScreen";

type Tab = "submit" | "status" | "list" | "profile";

export default function App() {
  // Placeholder "session" until real auth is added
  const [userId, setUserId] = useState<string | null>("kev");
  const [tab, setTab] = useState<Tab>("submit");

  if (!userId) {
    return (
      <SafeAreaView style={{ flex: 1, paddingTop: Platform.OS === "android" ? StatusBar.currentHeight : 0 }}>
        <Login onLogin={(id) => setUserId(id)} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, paddingTop: Platform.OS === "android" ? StatusBar.currentHeight : 0 }}>
      {/* Simple tabs */}
      <View style={{ flexDirection: "row", justifyContent: "space-around", padding: 8 }}>
        <Button title="Submit" onPress={() => setTab("submit")} />
        <Button title="Status" onPress={() => setTab("status")} />
        <Button title="Tickets" onPress={() => setTab("list")} />
        <Button title="Profile" onPress={() => setTab("profile")} />
      </View>

      <View style={{ flex: 1 }}>
        {tab === "submit" && <SubmitTicket />}
        {tab === "status" && <StatusCheck />}
        {tab === "list" && <TicketList userId={userId} />}
        {tab === "profile" && <ProfileScreen userId={userId} />}
      </View>
    </SafeAreaView>
  );
}
