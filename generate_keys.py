from pywebpush import webpush

# Generar claves VAPID
vapid_keys = webpush.generate_vapid_keys()

print("=" * 50)
print("🔑 CLAVES VAPID PARA NOTIFICACIONES PUSH")
print("=" * 50)
print()
print("📌 VAPID_PUBLIC_KEY (pública):")
print(vapid_keys['public_key'])
print()
print("🔒 VAPID_PRIVATE_KEY (privada - NO compartir):")
print(vapid_keys['private_key'])
print()
print("=" * 50)
print("✅ Copia estas claves en las variables de entorno de Render:")
print("   - VAPID_PUBLIC_KEY")
print("   - VAPID_PRIVATE_KEY")
print("=" * 50)