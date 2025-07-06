from datetime import datetime
import pytz

# Get IST timezone
ist = pytz.timezone('Asia/Kolkata')

# Get current IST time
ist_time = datetime.now(ist)

# Print IST time correctly
print("Current IST Time:", ist_time.strftime("%d/%m/%Y, %I:%M:%S %p"))
