"""Curated company profile knowledge base and cloud-resilient metadata provider for FinPulse AI.

Provides verified corporate summaries, founded years, industries, headquarters, and employee
statistics for top Indian NSE companies. This guarantees complete, reliable data on cloud hosting
(e.g., Streamlit Community Cloud) where external scraping APIs like Yahoo Finance frequently rate-limit
or block shared cloud datacenter IP ranges.
"""

from __future__ import annotations
import logging
import urllib.parse
import requests

LOGGER = logging.getLogger(__name__)

# Curated profiles for prominent NSE companies
NSE_COMPANY_PROFILES: dict[str, dict[str, str]] = {
    "RELIANCE.NS": {
        "summary": "Reliance Industries Limited is an Indian multinational conglomerate headquartered in Mumbai. Its businesses include energy, petrochemicals, natural gas, retail, telecommunications, mass media, and textiles. Reliance is one of the most profitable companies in India and the largest publicly traded company in India by market capitalization.",
        "industry": "Oil & Gas Refining & Marketing",
        "founded": "1958",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "389,414",
    },
    "TCS.NS": {
        "summary": "Tata Consultancy Services Limited (TCS) is an Indian multinational technology company specialising in information technology services and consulting. Headquartered in Mumbai, it operates in 150 locations across 46 countries and is the second largest Indian company by market capitalisation.",
        "industry": "Information Technology Services",
        "founded": "1968",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "601,546",
    },
    "HDFCBANK.NS": {
        "summary": "HDFC Bank Limited is an Indian banking and financial services company headquartered in Mumbai. It is India's largest private sector bank by assets and the world's fourth-largest bank by market capitalisation. The bank provides a vast suite of retail, wholesale, and digital banking products.",
        "industry": "Private Sector Banking & Financial Services",
        "founded": "1994",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "213,527",
    },
    "INFY.NS": {
        "summary": "Infosys Limited is an Indian multinational information technology company that provides business consulting, information technology and outsourcing services. Founded in Pune and headquartered in Bengaluru, Infosys is the second-largest Indian IT company by revenue.",
        "industry": "Information Technology Services",
        "founded": "1981",
        "headquarters": "Bengaluru, Karnataka, India",
        "employees": "317,240",
    },
    "ICICIBANK.NS": {
        "summary": "ICICI Bank Limited is a leading Indian multinational bank and financial services company. It offers a wide range of banking products and financial services for corporate and retail customers through a variety of delivery channels and specialised subsidiaries.",
        "industry": "Private Sector Banking",
        "founded": "1994",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "141,000",
    },
    "BHARTIARTL.NS": {
        "summary": "Bharti Airtel Limited is an Indian multinational telecommunications services company based in New Delhi. It operates in 18 countries across South Asia and Africa, providing 4G, 5G, mobile broadband, fixed-line telephone, and digital television services.",
        "industry": "Telecommunications Services",
        "founded": "1995",
        "headquarters": "New Delhi, Delhi, India",
        "employees": "62,500",
    },
    "SBIN.NS": {
        "summary": "State Bank of India (SBI) is an Indian multinational public sector bank and financial services statutory body headquartered in Mumbai. It is the 48th largest bank in the world by total assets and controls over a quarter of India's total banking market share.",
        "industry": "Public Sector Banking",
        "founded": "1955",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "232,296",
    },
    "ITC.NS": {
        "summary": "ITC Limited is an Indian conglomerate company headquartered in Kolkata. ITC has a diversified presence across industries such as FMCG, hotels, software, packaging, paperboards, specialty papers, and agribusiness.",
        "industry": "Consumer Goods & Conglomerate",
        "founded": "1910",
        "headquarters": "Kolkata, West Bengal, India",
        "employees": "28,225",
    },
    "HINDUNILVR.NS": {
        "summary": "Hindustan Unilever Limited (HUL) is an Indian consumer goods company headquartered in Mumbai. It is a subsidiary of the British company Unilever. Its products include foods, beverages, cleaning agents, personal care products, water purifiers, and other fast-moving consumer goods.",
        "industry": "Fast Moving Consumer Goods (FMCG)",
        "founded": "1933",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "21,000",
    },
    "LT.NS": {
        "summary": "Larsen & Toubro Limited (L&T) is an Indian multinational conglomerate company, with business interests in engineering, construction, manufacturing, technology, information technology and financial services, headquartered in Mumbai.",
        "industry": "Engineering & Construction",
        "founded": "1938",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "330,000",
    },
    "TATAMOTORS.NS": {
        "summary": "Tata Motors Limited is an Indian multinational automotive manufacturing company headquartered in Mumbai. It is part of the Tata Group and produces passenger cars, trucks, vans, coaches, and luxury vehicles through Jaguar Land Rover.",
        "industry": "Automotive Manufacturing",
        "founded": "1945",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "91,373",
    },
    "BAJFINANCE.NS": {
        "summary": "Bajaj Finance Limited is an Indian non-banking financial company (NBFC) headquartered in Pune. It is one of the leading financial services companies in India, with business focused on consumer lending, SME lending, commercial lending, and wealth management.",
        "industry": "Non-Banking Financial Services (NBFC)",
        "founded": "1987",
        "headquarters": "Pune, Maharashtra, India",
        "employees": "48,500",
    },
    "MARUTI.NS": {
        "summary": "Maruti Suzuki India Limited is an Indian automobile manufacturer based in New Delhi. A subsidiary of Japanese automaker Suzuki Motor Corporation, Maruti Suzuki is the market leader in the passenger car segment in India.",
        "industry": "Automotive Manufacturing",
        "founded": "1981",
        "headquarters": "New Delhi, Delhi, India",
        "employees": "40,000",
    },
    "AXISBANK.NS": {
        "summary": "Axis Bank Limited is an Indian multinational banking and financial services company headquartered in Mumbai. It is India's third largest private sector bank by assets, offering a comprehensive suite of financial services across retail, corporate, and SME banking.",
        "industry": "Private Sector Banking",
        "founded": "1993",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "104,000",
    },
    "SUNPHARMA.NS": {
        "summary": "Sun Pharmaceutical Industries Limited is an Indian multinational pharmaceutical company headquartered in Mumbai. It manufactures and sells pharmaceutical formulations and active pharmaceutical ingredients (APIs) in India, the US, and internationally.",
        "industry": "Pharmaceuticals & Biotechnology",
        "founded": "1983",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "41,000",
    },
    "TITAN.NS": {
        "summary": "Titan Company Limited is an Indian luxury fashion brand that manufactures watches, jewelry, eyewear, and fragrance. It is a joint venture between the Tata Group and the Tamil Nadu Industrial Development Corporation.",
        "industry": "Luxury Goods & Jewelry",
        "founded": "1984",
        "headquarters": "Bengaluru, Karnataka, India",
        "employees": "8,500",
    },
    "KOTAKBANK.NS": {
        "summary": "Kotak Mahindra Bank Limited is an Indian banking and financial services company headquartered in Mumbai. It offers personal finance, investment banking, life insurance, and wealth management across commercial and retail customers.",
        "industry": "Private Sector Banking",
        "founded": "1985",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "73,400",
    },
    "ADANIENT.NS": {
        "summary": "Adani Enterprises Limited is an Indian multinational publicly traded holding company and a part of the Adani Group. The company is primarily involved in mining, energy infrastructure, airport management, solar PV manufacturing, and defense.",
        "industry": "Conglomerate & Infrastructure",
        "founded": "1988",
        "headquarters": "Ahmedabad, Gujarat, India",
        "employees": "30,000",
    },
    "TATASTEEL.NS": {
        "summary": "Tata Steel Limited is an Indian multinational steel-making company based in Mumbai and headquartered in Kolkata. It is one of the top steel producers in the world with an annual crude steel capacity of 35 million tonnes.",
        "industry": "Steel & Metals",
        "founded": "1907",
        "headquarters": "Mumbai / Kolkata, India",
        "employees": "77,000",
    },
    "M&M.NS": {
        "summary": "Mahindra & Mahindra Limited is an Indian multinational automotive manufacturing corporation headquartered in Mumbai. It is one of the largest vehicle manufacturers by production in India and the largest manufacturer of tractors in the world.",
        "industry": "Automotive & Farm Equipment",
        "founded": "1945",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "260,000",
    },
    "WIPRO.NS": {
        "summary": "Wipro Limited is an Indian multinational corporation that provides information technology, consultant and business process services. Headquartered in Bengaluru, it is recognised globally for its comprehensive portfolio of services and strong commitment to sustainability.",
        "industry": "Information Technology Services",
        "founded": "1945",
        "headquarters": "Bengaluru, Karnataka, India",
        "employees": "234,000",
    },
    "ZOMATO.NS": {
        "summary": "Zomato is an Indian online food ordering and restaurant discovery platform headquartered in Gurugram. Founded in 2008, it connects customers, restaurant partners, and delivery partners across India and overseas.",
        "industry": "Internet & Consumer Services",
        "founded": "2008",
        "headquarters": "Gurugram, Haryana, India",
        "employees": "4,500",
    },
    "TRENT.NS": {
        "summary": "Trent Limited is an Indian retail company which is part of the Tata Group. Headquartered in Mumbai, Trent operates retail store chains including Westside, Zudio, Landmark, and Star Bazaar.",
        "industry": "Apparel & Department Retail",
        "founded": "1998",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "14,000",
    },
    "NTPC.NS": {
        "summary": "NTPC Limited is an Indian central public sector undertaking owned by the Ministry of Power. Headquartered in New Delhi, NTPC's core business is the generation and distribution of electricity across thermal, hydro, and renewable assets.",
        "industry": "Electric Utilities & Power Generation",
        "founded": "1975",
        "headquarters": "New Delhi, Delhi, India",
        "employees": "18,000",
    },
    "POWERGRID.NS": {
        "summary": "Power Grid Corporation of India Limited (POWERGRID) is an Indian central public sector enterprise under the Ministry of Power. Headquartered in Gurugram, it transmits approximately 50% of the total electricity generated in India on its transmission network.",
        "industry": "Electric Power Transmission",
        "founded": "1989",
        "headquarters": "Gurugram, Haryana, India",
        "employees": "8,500",
    },
    "BEL.NS": {
        "summary": "Bharat Electronics Limited (BEL) is an Indian state-owned aerospace and defense electronics company. Headquartered in Bengaluru, it manufactures advanced electronic products for the Indian Armed Forces and civilian applications.",
        "industry": "Aerospace & Defense Electronics",
        "founded": "1954",
        "headquarters": "Bengaluru, Karnataka, India",
        "employees": "8,800",
    },
    "HAL.NS": {
        "summary": "Hindustan Aeronautics Limited (HAL) is an Indian public sector aerospace and defense company headquartered in Bengaluru. Governed under the Ministry of Defence, HAL is actively involved in design, fabrication, and assembly of aircraft, jet engines, and helicopters.",
        "industry": "Aerospace & Defense",
        "founded": "1940",
        "headquarters": "Bengaluru, Karnataka, India",
        "employees": "28,000",
    },
    "COALINDIA.NS": {
        "summary": "Coal India Limited (CIL) is an Indian central public sector undertaking under the Ministry of Coal. Headquartered in Kolkata, it is the largest government-owned coal producer in the world.",
        "industry": "Coal Mining & Energy",
        "founded": "1975",
        "headquarters": "Kolkata, West Bengal, India",
        "employees": "239,000",
    },
    "ONGC.NS": {
        "summary": "Oil and Natural Gas Corporation (ONGC) is an Indian central public sector undertaking under the ownership of Ministry of Petroleum and Natural Gas. It is the largest crude oil and natural gas company in India, contributing around 71% to domestic production.",
        "industry": "Oil & Gas Exploration & Production",
        "founded": "1956",
        "headquarters": "New Delhi, Delhi, India",
        "employees": "26,000",
    },
    "IOC.NS": {
        "summary": "Indian Oil Corporation Limited (IOCL) is an Indian central public sector undertaking under the Ministry of Petroleum and Natural Gas. It is the largest state-owned oil corporation in the country with operations spanning refining, pipeline transportation, and marketing.",
        "industry": "Oil Refining & Distribution",
        "founded": "1959",
        "headquarters": "New Delhi, Delhi, India",
        "employees": "31,000",
    },
    "VEDL.NS": {
        "summary": "Vedanta Limited is an Indian multinational mining and natural resources company headquartered in Mumbai. Its principal operations are in iron ore, gold and aluminum mines in Goa, Karnataka, Rajasthan, and Odisha.",
        "industry": "Mining & Metals",
        "founded": "1979",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "78,000",
    },
    "JIOFIN.NS": {
        "summary": "Jio Financial Services Limited is an Indian financial services company demerged from Reliance Industries. It provides digital-first lending, insurance broking, payments solutions, and wealth management services across India.",
        "industry": "Financial Services & FinTech",
        "founded": "2023",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "1,200",
    },
    "HCLTECH.NS": {
        "summary": "HCL Technologies Limited is an Indian multinational information technology services and consulting company headquartered in Noida. It is among the top Indian IT services corporations, serving global enterprises across digital, engineering, and cloud.",
        "industry": "Information Technology Services",
        "founded": "1991",
        "headquarters": "Noida, Uttar Pradesh, India",
        "employees": "225,000",
    },
    "TECHM.NS": {
        "summary": "Tech Mahindra Limited is an Indian multinational information technology services and consulting company. Part of the Mahindra Group, it provides digital transformation, consulting, and business re-engineering services worldwide.",
        "industry": "Information Technology Services",
        "founded": "1986",
        "headquarters": "Pune, Maharashtra, India",
        "employees": "145,000",
    },
    "NESTLEIND.NS": {
        "summary": "Nestlé India Limited is the Indian subsidiary of Nestlé, a Swiss multinational food and beverage corporation. Headquartered in Gurugram, its products include milk, coffee, confectionery, and prepared cooking aids.",
        "industry": "Packaged Foods & Beverages",
        "founded": "1959",
        "headquarters": "Gurugram, Haryana, India",
        "employees": "8,000",
    },
    "ASIANPAINT.NS": {
        "summary": "Asian Paints Limited is an Indian multinational paint company headquartered in Mumbai. It is the largest paint company in India by market share and manufactures paints, coatings, home decor, and bath fittings.",
        "industry": "Paints & Home Decor",
        "founded": "1942",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "7,500",
    },
    "ULTRACEMCO.NS": {
        "summary": "UltraTech Cement Limited is an Indian multinational cement company based in Mumbai. It is the largest manufacturer of grey cement, ready-mix concrete (RMC), and white cement in India and the third largest globally.",
        "industry": "Building Materials & Cement",
        "founded": "1983",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "22,000",
    },
    "GRASIM.NS": {
        "summary": "Grasim Industries Limited is the flagship company of the Aditya Birla Group. Headquartered in Mumbai, its core businesses include viscose staple fibre, chemicals, paints (Birla Opus), and financial services.",
        "industry": "Textiles, Chemicals & Paints",
        "founded": "1947",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "24,000",
    },
    "HINDALCO.NS": {
        "summary": "Hindalco Industries Limited is an Indian aluminium and copper manufacturing company. It is a subsidiary of the Aditya Birla Group and, through Novelis, the world's largest aluminium rolling and recycling company.",
        "industry": "Aluminium & Copper Manufacturing",
        "founded": "1958",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "35,000",
    },
    "SHRIRAMFIN.NS": {
        "summary": "Shriram Finance Limited is a flagship company of the Shriram Group and India's largest retail non-banking financial company. It provides commercial vehicle finance, MSME loans, and two-wheeler finance across urban and rural markets.",
        "industry": "Non-Banking Financial Services (NBFC)",
        "founded": "1979",
        "headquarters": "Chennai, Tamil Nadu, India",
        "employees": "73,000",
    },
    "CIPLA.NS": {
        "summary": "Cipla Limited is an Indian multinational pharmaceutical company headquartered in Mumbai. Cipla primarily develops medicines to treat respiratory disease, cardiovascular disease, arthritis, diabetes, and other medical conditions.",
        "industry": "Pharmaceuticals",
        "founded": "1935",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "25,000",
    },
    "DRREDDY.NS": {
        "summary": "Dr. Reddy's Laboratories is an Indian multinational pharmaceutical company based in Hyderabad. It manufactures and markets a wide range of pharmaceuticals in India and overseas across generic formulations and active ingredients.",
        "industry": "Pharmaceuticals & Generics",
        "founded": "1984",
        "headquarters": "Hyderabad, Telangana, India",
        "employees": "26,000",
    },
    "APOLLOHOSP.NS": {
        "summary": "Apollo Hospitals Enterprise Limited is an Indian multinational healthcare group headquartered in Chennai. It is the largest private healthcare service provider in India with a wide network of multi-speciality hospitals and pharmacies.",
        "industry": "Healthcare & Hospital Chains",
        "founded": "1983",
        "headquarters": "Chennai, Tamil Nadu, India",
        "employees": "70,000",
    },
    "EICHERMOT.NS": {
        "summary": "Eicher Motors Limited is an Indian multinational automotive manufacturer that produces motorcycles and commercial vehicles. It is the parent company of Royal Enfield, an iconic manufacturer of middleweight motorcycles.",
        "industry": "Automotive Manufacturing",
        "founded": "1948",
        "headquarters": "New Delhi, Delhi, India",
        "employees": "5,000",
    },
    "DIVISLAB.NS": {
        "summary": "Divi's Laboratories Limited is an Indian multinational pharmaceutical company and producer of active pharmaceutical ingredients (APIs) and intermediates, headquartered in Hyderabad.",
        "industry": "Pharmaceutical APIs & Intermediates",
        "founded": "1990",
        "headquarters": "Hyderabad, Telangana, India",
        "employees": "17,000",
    },
    "BPCL.NS": {
        "summary": "Bharat Petroleum Corporation Limited (BPCL) is an Indian central public sector undertaking under the Ministry of Petroleum and Natural Gas. It operates refineries in Mumbai and Kochi and a nationwide fuel distribution network.",
        "industry": "Oil Refining & Marketing",
        "founded": "1952",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "9,000",
    },
    "BAJAJ-AUTO.NS": {
        "summary": "Bajaj Auto Limited is an Indian multinational automotive manufacturing company based in Pune. It manufactures motorcycles, scooters, and auto rickshaws, and is the world's third-largest manufacturer of motorcycles.",
        "industry": "Two & Three Wheeler Automotive",
        "founded": "1945",
        "headquarters": "Pune, Maharashtra, India",
        "employees": "10,000",
    },
    "HEROMOTOCO.NS": {
        "summary": "Hero MotoCorp Limited is an Indian multinational motorcycle and scooter manufacturer headquartered in New Delhi. It is the world's largest manufacturer of two-wheelers by volume.",
        "industry": "Automotive Manufacturing",
        "founded": "1984",
        "headquarters": "New Delhi, Delhi, India",
        "employees": "9,200",
    },
    "BRITANNIA.NS": {
        "summary": "Britannia Industries Limited is an Indian food company that is part of the Wadia Group. Headquartered in Kolkata, it sells Britannia and Tiger brands of biscuits, breads, and dairy products throughout India and internationally.",
        "industry": "Packaged Foods & Confectionery",
        "founded": "1892",
        "headquarters": "Kolkata, West Bengal, India",
        "employees": "4,500",
    },
    "INDUSINDBK.NS": {
        "summary": "IndusInd Bank Limited is an Indian new-generation private bank headquartered in Mumbai. It offers commercial, transactional, and electronic banking products and services across retail and institutional clients.",
        "industry": "Private Sector Banking",
        "founded": "1994",
        "headquarters": "Mumbai, Maharashtra, India",
        "employees": "38,000",
    },
    "PERSISTENT.NS": {
        "summary": "Persistent Systems is an Indian multinational technology services company delivering software engineering, enterprise modernization, and digital transformation for global enterprises.",
        "industry": "Information Technology Services",
        "founded": "1990",
        "headquarters": "Pune, Maharashtra, India",
        "employees": "23,800",
    },
    "VBL.NS": {
        "summary": "Varun Beverages Limited is an Indian company that produces, bottles, and distributes beverages. It is the second-largest bottling partner of PepsiCo in the world outside the United States.",
        "industry": "Beverages & Bottling",
        "founded": "1995",
        "headquarters": "Gurugram, Haryana, India",
        "employees": "13,000",
    },
    "COFORGE.NS": {
        "summary": "Coforge Limited is an Indian multinational information technology services and consulting company based in Noida. It specializes in application development, cloud computing, and AI-driven business modernization.",
        "industry": "Information Technology Services",
        "founded": "1992",
        "headquarters": "Noida, Uttar Pradesh, India",
        "employees": "24,000",
    },
    "MPHASIS.NS": {
        "summary": "Mphasis Limited is an Indian multinational information technology services and consulting company based in Bengaluru. It specializes in cloud and cognitive services for banking and financial sectors.",
        "industry": "Information Technology Services",
        "founded": "1992",
        "headquarters": "Bengaluru, Karnataka, India",
        "employees": "33,000",
    },
}


def fetch_fallback_wikipedia_profile(company_name: str) -> dict[str, str] | None:
    """Fetch high-quality summary from Wikipedia REST API as an unblocked cloud fallback."""
    try:
        clean_name = company_name.split("(")[0].strip()
        search_terms = [
            f"{clean_name} Limited",
            f"{clean_name} (company)",
            f"{clean_name} Ltd",
            clean_name,
            f"{clean_name} India",
        ]
        if "limited" in clean_name.lower() or "ltd" in clean_name.lower():
            search_terms.insert(0, clean_name)

        headers = {"User-Agent": "FinPulseAI/1.0 (academic finance research prototype; contact@finpulse.org)"}
        non_company_indicators = ("episode", "television series", "album", "song", "film", "collegiate athletic conference")

        for term in search_terms:
            safe_title = urllib.parse.quote(term.replace(" ", "_"))
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("type") == "disambiguation":
                    continue
                description = (data.get("description") or "").strip()
                if any(ind in description.lower() for ind in non_company_indicators):
                    continue
                extract = data.get("extract", "")
                if extract and len(extract) > 40:
                    ind_val = description if description else "Publicly listed company on NSE India"
                    return {
                        "summary": extract,
                        "industry": ind_val,
                        "founded": "Not available",
                        "headquarters": "India",
                        "employees": "Not available",
                    }
    except Exception as exc:
        LOGGER.debug("Wikipedia fallback lookup failed for %s: %s", company_name, exc)
    return None

