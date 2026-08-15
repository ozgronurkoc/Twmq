import { ImageResponse } from "next/og";

// Ikon TSX olarak uretilir (next/og) — projeye .svg ya da .html dosyasi
// eklemeye gerek kalmaz.
export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #7c3aed 0%, #4f6ef2 100%)",
          borderRadius: 7,
          color: "white",
          fontSize: 17,
          fontWeight: 700,
          letterSpacing: -1,
        }}
      >
        14
      </div>
    ),
    { ...size },
  );
}
