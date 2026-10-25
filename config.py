import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "smart-blood-bank-super-secret-key-2026")
    MONGO_URI = os.getenv("MONGO_URI", "").strip()
    DB_NAME = os.getenv("DB_NAME", "smart_blood_bank")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    SMS_GATEWAY_API_KEY = os.getenv("SMS_GATEWAY_API_KEY", "").strip()
    WHATSAPP_BUSINESS_API_KEY = os.getenv("WHATSAPP_BUSINESS_API_KEY", "").strip()
    
    # Reverse proxy support
    PREFERRED_URL_SCHEME = "https"
    
    # Standard ABO, Rh, and rare blood groups
    BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "Bombay Blood Group (hh)"]
    BLOOD_GROUP_FULL_NAMES = {
        "A+": "A Positive",
        "A-": "A Negative",
        "B+": "B Positive",
        "B-": "B Negative",
        "O+": "O Positive",
        "O-": "O Negative",
        "AB+": "AB Positive",
        "AB-": "AB Negative",
        "Bombay Blood Group (hh)": "Bombay Blood Group (hh)"
    }
    
    # Blood donation gap rule (days)
    DONATION_GAP_DAYS = 90
    
    # Complete Indian States & Union Territories with authentic major districts
    INDIAN_LOCATIONS = {
        "Andhra Pradesh": ["Visakhapatnam", "Vijayawada (NTR)", "Guntur", "Tirupati", "Kurnool", "Kakinada", "Nellore", "Anantapur", "Kadapa", "Rajahmundry"],
        "Arunachal Pradesh": ["Itanagar (Papum Pare)", "Naharlagun", "Pasighat", "Tawang", "Ziro", "Changlang"],
        "Assam": ["Guwahati (Kamrup Metro)", "Dibrugarh", "Silchar (Cachar)", "Jorhat", "Nagaon", "Tezpur (Sonitpur)", "Tinsukia", "Barpeta"],
        "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga", "Purnia", "Begusarai", "Ara (Bhojpur)", "Munger"],
        "Chandigarh": ["Chandigarh"],
        "Chhattisgarh": ["Raipur", "Bilaspur", "Durg-Bhilai", "Korba", "Rajnandgaon", "Jagdalpur (Bastar)", "Ambikapur (Surguja)"],
        "Delhi (NCR)": ["Central Delhi", "East Delhi", "New Delhi", "North Delhi", "North East Delhi", "North West Delhi", "South Delhi", "South East Delhi", "South West Delhi", "West Delhi", "Shahdara"],
        "Goa": ["North Goa (Panaji)", "South Goa (Margao)", "Vasco da Gama", "Mapusa", "Ponda"],
        "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar", "Bhavnagar", "Jamnagar", "Junagadh", "Anand", "Navsari", "Kutch (Bhuj)"],
        "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Karnal", "Rohtak", "Hisar", "Panchkula", "Sonipat", "Yamunanagar"],
        "Himachal Pradesh": ["Shimla", "Dharamshala (Kangra)", "Mandi", "Solan", "Kullu", "Hamirpur", "Bilaspur", "Una"],
        "Jammu & Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla", "Udhampur", "Kathua", "Pulwama", "Kupwara"],
        "Jharkhand": ["Ranchi", "Jamshedpur (East Singhbhum)", "Dhanbad", "Bokaro", "Deoghar", "Hazaribagh", "Giridih", "Dumka"],
        "Karnataka": ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Mangaluru (Dakshina Kannada)", "Hubballi-Dharwad", "Belagavi", "Davanagere", "Kalaburagi", "Ballari", "Shivamogga", "Udupi", "Tumakuru"],
        "Kerala": ["Thiruvananthapuram", "Kochi (Ernakulam)", "Kozhikode", "Thrissur", "Kollam", "Kannur", "Palakkad", "Kottayam", "Malappuram", "Alappuzha", "Idukki", "Wayanad", "Kasaragod", "Pathanamthitta"],
        "Ladakh": ["Leh", "Kargil"],
        "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain", "Sagar", "Dewas", "Satna", "Ratlam", "Rewa"],
        "Maharashtra": ["Mumbai City", "Mumbai Suburban", "Pune", "Nagpur", "Thane", "Nashik", "Chhatrapati Sambhajinagar (Aurangabad)", "Solapur", "Kolhapur", "Amravati", "Nanded", "Jalgaon", "Navi Mumbai"],
        "Manipur": ["Imphal East", "Imphal West", "Churachandpur", "Thoubal", "Bishnupur"],
        "Meghalaya": ["East Khasi Hills (Shillong)", "West Garo Hills (Tura)", "Ri-Bhoi", "Jaintia Hills"],
        "Mizoram": ["Aizawl", "Lunglei", "Champhai", "Kolasib"],
        "Nagaland": ["Kohima", "Dimapur", "Mokokchung", "Tuensang", "Wokha"],
        "Odisha": ["Bhubaneswar (Khurda)", "Cuttack", "Rourkela (Sundargarh)", "Berhampur (Ganjam)", "Sambalpur", "Puri", "Balasore", "Bhadrak", "Baripada (Mayurbhanj)"],
        "Puducherry": ["Puducherry", "Karaikal", "Mahe", "Yanam"],
        "Punjab": ["Amritsar", "Ludhiana", "Jalandhar", "Patiala", "Mohali (SAS Nagar)", "Bathinda", "Hoshiarpur", "Pathankot", "Moga"],
        "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Alwar", "Bhilwara", "Sikar", "Bharatpur", "Pali"],
        "Sikkim": ["East Sikkim (Gangtok)", "South Sikkim (Namchi)", "West Sikkim (Geyzing)", "North Sikkim (Mangan)"],
        "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Vellore", "Erode", "Thanjavur", "Dindigul", "Kanchipuram", "Tiruppur", "Thoothukudi", "Nagercoil (Kanyakumari)"],
        "Telangana": ["Hyderabad", "Rangareddy", "Medchal-Malkajgiri", "Warangal", "Nizamabad", "Karimnagar", "Khammam", "Nalgonda", "Mahabubnagar"],
        "Tripura": ["West Tripura (Agartala)", "Gomati", "Dhalai", "North Tripura"],
        "Uttar Pradesh": ["Lucknow", "Kanpur Nagar", "Varanasi", "Noida (Gautam Buddha Nagar)", "Ghaziabad", "Agra", "Prayagraj", "Meerut", "Bareilly", "Aligarh", "Gorakhpur", "Moradabad", "Saharanpur", "Jhansi", "Ayodhya"],
        "Uttarakhand": ["Dehradun", "Haridwar", "Nainital", "Roorkee", "Haldwani", "Rishikesh", "Udham Singh Nagar"],
        "West Bengal": ["Kolkata", "North 24 Parganas", "South 24 Parganas", "Howrah", "Darjeeling", "Paschim Bardhaman (Asansol/Durgapur)", "Siliguri", "Hooghly", "Murshidabad", "Nadia", "Malda"]
    }
