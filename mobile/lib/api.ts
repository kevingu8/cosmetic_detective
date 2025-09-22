import axios from "axios";

// iOS Simulator can use 127.0.0.1; real phone needs your Mac's LAN IP (e.g. http://192.168.1.20:8000)
export const API_BASE = "http://127.0.0.1:8000";

export type Ticket = {
  id: string;
  user_id?: string | null;
  brand: string;
  category: string;
  notes?: string | null;
  images: string[];
  status: "submitted" | "in_review" | "resolved" | "need_more_info" | "rejected";
  assigned_reviewer_id?: string | null;
  claimed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type Result = {
  ticket_id: string;
  verdict: "authentic" | "inauthentic" | "undetermined";
  rationale?: string | null;
  reviewer_id?: string | null;
  reviewed_at: string;
};

export async function createTicket(params: {
  brand: string;
  category: string;
  notes?: string;
  user_id?: string;
  images: { uri: string; name: string; type: string }[];
}) {
  const form = new FormData();
  form.append("brand", params.brand);
  form.append("category", params.category);
  form.append("notes", params.notes ?? "");
  form.append("user_id", params.user_id ?? "kev");

  params.images.forEach((img) => {
    // @ts-ignore (React Native FormData file)
    form.append("images", { uri: img.uri, name: img.name, type: img.type });
  });

  const res = await axios.post(`${API_BASE}/tickets`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    transformRequest: (d) => d,
  });
  return res.data as Ticket;
}

export async function getTicket(ticketId: string) {
  const res = await axios.get(`${API_BASE}/tickets/${ticketId}`);
  return res.data as Ticket;
}

export async function getResult(ticketId: string) {
  const res = await axios.get(`${API_BASE}/tickets/${ticketId}/result`);
  return res.data as Result;
}
