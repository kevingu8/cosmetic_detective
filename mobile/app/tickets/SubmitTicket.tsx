import React, { useState } from "react";
import { View, Text, TextInput, Button, Image, ScrollView, Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { createTicket } from "../../lib/api";

export default function SubmitTicket() {
  const [brand, setBrand] = useState("Dior");
  const [category, setCategory] = useState("lipstick");
  const [notes, setNotes] = useState("");
  const [images, setImages] = useState<{ uri: string; name: string; type: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const maxImages = 5;

  async function pickFromLibrary() {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Permission required", "Please allow photo library access.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      allowsMultipleSelection: true,
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.9,
      selectionLimit: maxImages - images.length,
    });
    if (!result.canceled) {
      const picked = result.assets.map((a, i) => ({
        uri: a.uri,
        name: `image_${Date.now()}_${i}.jpg`,
        type: "image/jpeg",
      }));
      setImages((prev) => [...prev, ...picked].slice(0, maxImages));
    }
  }

  async function takePhoto() {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Permission required", "Please allow camera access.");
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.9 });
    if (!result.canceled) {
      const a = result.assets[0];
      setImages((prev) =>
        [...prev, { uri: a.uri, name: `camera_${Date.now()}.jpg`, type: "image/jpeg" }].slice(0, maxImages)
      );
    }
  }

  async function onSubmit() {
    if (!brand.trim() || !category.trim()) {
      Alert.alert("Missing fields", "Brand and category are required.");
      return;
    }
    if (images.length === 0) {
      Alert.alert("No images", "Please add at least one image.");
      return;
    }
    setSubmitting(true);
    try {
      const t = await createTicket({ brand, category, notes, user_id: "kev", images });
      Alert.alert("Submitted ✅", `Ticket ID:\n${t.id}`);
      // Optionally reset:
      // setImages([]); setNotes("");
    } catch (e: any) {
      Alert.alert("Submit failed", e?.response?.data?.detail || e?.message || "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
      <Text style={{ fontSize: 22, fontWeight: "600" }}>Submit Ticket</Text>

      <Text>Brand</Text>
      <TextInput
        value={brand}
        onChangeText={setBrand}
        placeholder="e.g., Dior"
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />

      <Text>Category</Text>
      <TextInput
        value={category}
        onChangeText={setCategory}
        placeholder="e.g., lipstick"
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8 }}
      />

      <Text>Notes (optional)</Text>
      <TextInput
        value={notes}
        onChangeText={setNotes}
        placeholder="Anything the reviewer should know"
        multiline
        style={{ borderWidth: 1, borderColor: "#ccc", padding: 10, borderRadius: 8, minHeight: 80 }}
      />

      <View style={{ flexDirection: "row", gap: 8 }}>
        <Button title="Pick from Library" onPress={pickFromLibrary} />
        <Button title="Take Photo" onPress={takePhoto} />
      </View>
      <Text>{images.length}/{maxImages} images</Text>

      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {images.map((img, idx) => (
          <Image key={idx} source={{ uri: img.uri }} style={{ width: 100, height: 100, borderRadius: 8 }} />
        ))}
      </View>

      <Button title={submitting ? "Submitting..." : "Submit Ticket"} onPress={onSubmit} disabled={submitting} />
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}
