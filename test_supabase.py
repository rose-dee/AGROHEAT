from database.supabase_client import test_connection

success, message = test_connection()

print("BERHASIL:" if success else "GAGAL:", message)