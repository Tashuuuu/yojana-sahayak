
import csv
import shutil
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "schemes.csv"
BACKUP_PATH = BASE_DIR / "data" / "schemes.backup.csv"

COLUMNS = [
    "scheme_id", "name_en", "name_hi", "lang",
    "section", "text", "source_url", "retrieved_on"
]

TODAY = date.today().isoformat()

# Existing PM-KISAN and PMUY records are preserved.
# Hindi equivalents are added below.
EXISTING_HINDI = {
    ("PMKISAN", "overview"):
        "पीएम-किसान एक केंद्रीय क्षेत्र की योजना है जिसका पूरा वित्तपोषण भारत सरकार करती है। यह योजना 1 दिसंबर 2018 से लागू हुई। इसका उद्देश्य भूमिधारक किसान परिवारों की वित्तीय आवश्यकताओं को पूरा करने के लिए आय सहायता प्रदान करना है।",

    ("PMKISAN", "benefits"):
        "पीएम-किसान के अंतर्गत पात्र भूमिधारक किसान परिवारों को प्रति वर्ष 6,000 रुपये की वित्तीय सहायता दी जाती है। यह राशि लाभार्थियों के बैंक खातों में तीन समान किस्तों में सीधे भेजी जाती है। प्रत्येक किस्त 2,000 रुपये की होती है।",

    ("PMKISAN", "eligibility"):
        "राज्य और केंद्र शासित प्रदेश के प्रशासन द्वारा पहचाने गए भूमिधारक किसान परिवार योजना के दिशानिर्देशों और अपवर्जन मानदंडों के अधीन पात्र होते हैं। संस्थागत भूमिधारक, कुछ संवैधानिक पदाधिकारी, निर्दिष्ट सरकारी कर्मचारी और पेंशनभोगी, आयकरदाता तथा कुछ पंजीकृत पेशेवर अपात्र श्रेणियों में शामिल हैं। लाभार्थियों को अनिवार्य ई-केवाईसी पूरी करनी चाहिए और आधिकारिक पोर्टल पर अपनी स्थिति जांचनी चाहिए।",

    ("PMUY", "overview"):
        "प्रधानमंत्री उज्ज्वला योजना भारत सरकार के पेट्रोलियम और प्राकृतिक गैस मंत्रालय के अंतर्गत संचालित योजना है। इसका उद्देश्य गरीब परिवारों की पात्र महिलाओं को बिना जमा राशि के एलपीजी कनेक्शन प्रदान करना है, ताकि स्वच्छ खाना पकाने के ईंधन तक उनकी पहुंच बेहतर हो सके।",

    ("PMUY", "eligibility"):
        "आवेदक महिला की आयु कम से कम 18 वर्ष होनी चाहिए। उसे निर्धारित वंचना घोषणा के अनुसार गरीब परिवार से संबंधित होना चाहिए। उसी परिवार में किसी तेल विपणन कंपनी का अन्य एलपीजी कनेक्शन नहीं होना चाहिए।",

    ("PMUY", "benefits_and_documents"):
        "पात्र उज्ज्वला लाभार्थियों को बिना सुरक्षा जमा और बिना स्थापना शुल्क के एलपीजी कनेक्शन मिलता है। कनेक्शन पैकेज में सिलेंडर, घरेलू प्रेशर रेगुलेटर, सुरक्षा होज़ और उपभोक्ता पुस्तिका शामिल हैं। आवेदन के लिए केवाईसी आवेदन, पहचान और पते के दस्तावेज, परिवार की संरचना का दस्तावेज, बैंक खाते का विवरण और वंचना घोषणा की आवश्यकता होती है। नवीनतम लाभ और दस्तावेजों के लिए आधिकारिक पोर्टल देखें।"
}

# Each new scheme has a conservative overview in English and Hindi.
# These descriptions are introductory, not complete eligibility guidelines.
NEW_SCHEMES = [
    {
        "id": "PMFBY",
        "en": "Pradhan Mantri Fasal Bima Yojana",
        "hi": "प्रधानमंत्री फसल बीमा योजना",
        "url": "https://pmfby.gov.in/",
        "text_en": "Pradhan Mantri Fasal Bima Yojana is a Government of India crop insurance scheme. It aims to provide insurance protection to farmers against crop losses arising from specified natural risks and unforeseen events, subject to scheme guidelines.",
        "text_hi": "प्रधानमंत्री फसल बीमा योजना भारत सरकार की फसल बीमा योजना है। इसका उद्देश्य योजना के दिशानिर्देशों के अनुसार निर्दिष्ट प्राकृतिक जोखिमों और अप्रत्याशित घटनाओं से होने वाले फसल नुकसान के विरुद्ध किसानों को बीमा सुरक्षा प्रदान करना है।"
    },
    {
        "id": "KCC",
        "en": "Kisan Credit Card Scheme",
        "hi": "किसान क्रेडिट कार्ड योजना",
        "url": "https://fasalrin.gov.in/",
        "text_en": "The Kisan Credit Card scheme facilitates access to timely and adequate credit for farmers for agricultural and related activities. Credit is provided through participating financial institutions subject to applicable rules.",
        "text_hi": "किसान क्रेडिट कार्ड योजना किसानों को कृषि और संबंधित गतिविधियों के लिए समय पर और पर्याप्त ऋण उपलब्ध कराने में सहायता करती है। लागू नियमों के अनुसार भाग लेने वाले वित्तीय संस्थानों के माध्यम से ऋण प्रदान किया जाता है।"
    },
    {
        "id": "PMKMY",
        "en": "Pradhan Mantri Kisan Maandhan Yojana",
        "hi": "प्रधानमंत्री किसान मानधन योजना",
        "url": "https://pmkmy.gov.in/",
        "text_en": "Pradhan Mantri Kisan Maandhan Yojana is a contributory pension scheme intended to provide social security to eligible small and marginal farmers in their old age, subject to scheme conditions.",
        "text_hi": "प्रधानमंत्री किसान मानधन योजना एक अंशदायी पेंशन योजना है। इसका उद्देश्य योजना की शर्तों के अनुसार पात्र छोटे और सीमांत किसानों को वृद्धावस्था में सामाजिक सुरक्षा प्रदान करना है।"
    },
    {
        "id": "SSY",
        "en": "Sukanya Samriddhi Yojana",
        "hi": "सुकन्या समृद्धि योजना",
        "url": "https://www.indiapost.gov.in/",
        "text_en": "Sukanya Samriddhi Yojana is a Government of India small savings scheme designed to support the financial future of a girl child. Accounts are governed by the applicable scheme rules.",
        "text_hi": "सुकन्या समृद्धि योजना भारत सरकार की एक लघु बचत योजना है। इसका उद्देश्य बालिका के वित्तीय भविष्य को सुरक्षित करने में सहायता करना है। इस योजना के खाते लागू नियमों के अनुसार संचालित होते हैं।"
    },
    {
        "id": "PMJAY",
        "en": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana",
        "hi": "आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना",
        "url": "https://pmjay.gov.in/",
        "text_en": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana is a publicly funded health assurance initiative. It provides eligible beneficiaries access to covered hospital care through empanelled healthcare providers, subject to scheme rules.",
        "text_hi": "आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना सार्वजनिक रूप से वित्तपोषित स्वास्थ्य आश्वासन पहल है। इसके अंतर्गत पात्र लाभार्थियों को योजना के नियमों के अनुसार सूचीबद्ध स्वास्थ्य संस्थानों में निर्धारित अस्पताल उपचार की सुविधा मिलती है।"
    },
    {
        "id": "JSY",
        "en": "Janani Suraksha Yojana",
        "hi": "जननी सुरक्षा योजना",
        "url": "https://nhm.gov.in/",
        "text_en": "Janani Suraksha Yojana is a safe motherhood intervention under the National Health Mission. It aims to promote institutional delivery among eligible pregnant women and reduce maternal and newborn risks.",
        "text_hi": "जननी सुरक्षा योजना राष्ट्रीय स्वास्थ्य मिशन के अंतर्गत सुरक्षित मातृत्व से जुड़ी पहल है। इसका उद्देश्य पात्र गर्भवती महिलाओं में संस्थागत प्रसव को प्रोत्साहित करना तथा मातृ और नवजात शिशु से जुड़े जोखिमों को कम करना है।"
    },
    {
        "id": "MI",
        "en": "Mission Indradhanush",
        "hi": "मिशन इंद्रधनुष",
        "url": "https://nhm.gov.in/",
        "text_en": "Mission Indradhanush is an immunisation initiative of the Government of India. It focuses on improving vaccination coverage among children and pregnant women who have missed routine immunisation services.",
        "text_hi": "मिशन इंद्रधनुष भारत सरकार की टीकाकरण पहल है। इसका उद्देश्य उन बच्चों और गर्भवती महिलाओं तक टीकाकरण सेवाएं पहुंचाना है जो नियमित टीकाकरण से छूट गए हैं।"
    },
    {
        "id": "PMAYG",
        "en": "Pradhan Mantri Awas Yojana Gramin",
        "hi": "प्रधानमंत्री आवास योजना ग्रामीण",
        "url": "https://pmayg.nic.in/",
        "text_en": "Pradhan Mantri Awas Yojana Gramin is a rural housing programme that aims to support eligible rural households in obtaining pucca houses with basic amenities, subject to programme guidelines.",
        "text_hi": "प्रधानमंत्री आवास योजना ग्रामीण एक ग्रामीण आवास कार्यक्रम है। इसका उद्देश्य कार्यक्रम के दिशानिर्देशों के अनुसार पात्र ग्रामीण परिवारों को बुनियादी सुविधाओं सहित पक्के मकान प्राप्त करने में सहायता करना है।"
    },
    {
        "id": "PMAYU",
        "en": "Pradhan Mantri Awas Yojana Urban",
        "hi": "प्रधानमंत्री आवास योजना शहरी",
        "url": "https://pmay-urban.gov.in/",
        "text_en": "Pradhan Mantri Awas Yojana Urban is a government housing mission focused on addressing urban housing needs. Its components and assistance are governed by the applicable mission guidelines.",
        "text_hi": "प्रधानमंत्री आवास योजना शहरी एक सरकारी आवास मिशन है जिसका उद्देश्य शहरी आवास संबंधी आवश्यकताओं को पूरा करना है। इसके विभिन्न घटक और सहायता लागू मिशन दिशानिर्देशों के अनुसार निर्धारित होते हैं।"
    },
    {
        "id": "SBM",
        "en": "Swachh Bharat Mission",
        "hi": "स्वच्छ भारत मिशन",
        "url": "https://swachhbharatmission.ddws.gov.in/",
        "text_en": "Swachh Bharat Mission is a national cleanliness and sanitation initiative. It promotes sanitation facilities, hygiene practices and improved waste management through its applicable rural and urban programmes.",
        "text_hi": "स्वच्छ भारत मिशन राष्ट्रीय स्वच्छता और सफाई से जुड़ी पहल है। इसके ग्रामीण और शहरी कार्यक्रमों के माध्यम से स्वच्छता सुविधाओं, स्वास्थ्यकर आदतों और बेहतर कचरा प्रबंधन को प्रोत्साहित किया जाता है।"
    },
    {
        "id": "PMJDY",
        "en": "Pradhan Mantri Jan-Dhan Yojana",
        "hi": "प्रधानमंत्री जन-धन योजना",
        "url": "https://pmjdy.gov.in/",
        "text_en": "Pradhan Mantri Jan-Dhan Yojana is a national financial inclusion mission. It aims to ensure access to basic banking services, savings and deposit accounts, remittance, credit, insurance and pension services.",
        "text_hi": "प्रधानमंत्री जन-धन योजना राष्ट्रीय वित्तीय समावेशन मिशन है। इसका उद्देश्य लोगों को बुनियादी बैंकिंग सेवाओं, बचत और जमा खातों, धन हस्तांतरण, ऋण, बीमा और पेंशन सेवाओं तक पहुंच प्रदान करना है।"
    },
    {
        "id": "APY",
        "en": "Atal Pension Yojana",
        "hi": "अटल पेंशन योजना",
        "url": "https://financialservices.gov.in/",
        "text_en": "Atal Pension Yojana is a pension scheme intended to strengthen old-age income security, particularly for workers in the unorganised sector. Participation is subject to the scheme's eligibility and contribution rules.",
        "text_hi": "अटल पेंशन योजना वृद्धावस्था में आय सुरक्षा को मजबूत करने के उद्देश्य से बनाई गई पेंशन योजना है। इसका विशेष ध्यान असंगठित क्षेत्र के श्रमिकों पर है। इसमें भागीदारी योजना की पात्रता और अंशदान संबंधी शर्तों के अधीन है।"
    },
    {
        "id": "PMJJBY",
        "en": "Pradhan Mantri Jeevan Jyoti Bima Yojana",
        "hi": "प्रधानमंत्री जीवन ज्योति बीमा योजना",
        "url": "https://jansuraksha.gov.in/",
        "text_en": "Pradhan Mantri Jeevan Jyoti Bima Yojana is a renewable life insurance scheme offered through participating banks and insurers. Coverage is subject to the applicable policy terms and eligibility conditions.",
        "text_hi": "प्रधानमंत्री जीवन ज्योति बीमा योजना भाग लेने वाले बैंकों और बीमा कंपनियों के माध्यम से उपलब्ध नवीकरणीय जीवन बीमा योजना है। बीमा सुरक्षा लागू पॉलिसी शर्तों और पात्रता मानदंडों के अधीन है।"
    },
    {
        "id": "PMSBY",
        "en": "Pradhan Mantri Suraksha Bima Yojana",
        "hi": "प्रधानमंत्री सुरक्षा बीमा योजना",
        "url": "https://jansuraksha.gov.in/",
        "text_en": "Pradhan Mantri Suraksha Bima Yojana is a renewable personal accident insurance scheme. It provides specified accident-related coverage to eligible subscribers according to the policy conditions.",
        "text_hi": "प्रधानमंत्री सुरक्षा बीमा योजना नवीकरणीय व्यक्तिगत दुर्घटना बीमा योजना है। यह पॉलिसी की शर्तों के अनुसार पात्र ग्राहकों को दुर्घटना से संबंधित निर्धारित बीमा सुरक्षा प्रदान करती है।"
    },
    {
        "id": "PMMY",
        "en": "Pradhan Mantri MUDRA Yojana",
        "hi": "प्रधानमंत्री मुद्रा योजना",
        "url": "https://www.mudra.org.in/",
        "text_en": "Pradhan Mantri MUDRA Yojana facilitates institutional credit for eligible micro enterprises and small business activities. Loans are provided through participating lending institutions under applicable lending rules.",
        "text_hi": "प्रधानमंत्री मुद्रा योजना पात्र सूक्ष्म उद्यमों और छोटे व्यवसायों के लिए संस्थागत ऋण की सुविधा प्रदान करती है। लागू ऋण नियमों के अनुसार भाग लेने वाले ऋण संस्थानों के माध्यम से ऋण दिया जाता है।"
    },
    {
        "id": "MGNREGA",
        "en": "Mahatma Gandhi National Rural Employment Guarantee Act",
        "hi": "महात्मा गांधी राष्ट्रीय ग्रामीण रोजगार गारंटी अधिनियम",
        "url": "https://nrega.nic.in/",
        "text_en": "The Mahatma Gandhi National Rural Employment Guarantee Act provides a legal framework for wage employment to rural households whose adult members volunteer to undertake unskilled manual work, subject to the Act and programme rules.",
        "text_hi": "महात्मा गांधी राष्ट्रीय ग्रामीण रोजगार गारंटी अधिनियम उन ग्रामीण परिवारों को मजदूरी आधारित रोजगार का कानूनी ढांचा प्रदान करता है जिनके वयस्क सदस्य अकुशल शारीरिक कार्य करने के लिए स्वेच्छा से तैयार होते हैं। यह अधिनियम और कार्यक्रम के नियमों के अधीन है।"
    },
    {
        "id": "PMKVY",
        "en": "Pradhan Mantri Kaushal Vikas Yojana",
        "hi": "प्रधानमंत्री कौशल विकास योजना",
        "url": "https://www.msde.gov.in/",
        "text_en": "Pradhan Mantri Kaushal Vikas Yojana is a skill development initiative intended to support skill training and certification for eligible candidates. Its training provisions are governed by the applicable programme guidelines.",
        "text_hi": "प्रधानमंत्री कौशल विकास योजना कौशल विकास की पहल है जिसका उद्देश्य पात्र उम्मीदवारों को कौशल प्रशिक्षण और प्रमाणन में सहायता प्रदान करना है। इसके प्रशिक्षण प्रावधान लागू कार्यक्रम दिशानिर्देशों के अनुसार संचालित होते हैं।"
    },
    {
        "id": "NMMS",
        "en": "National Means-cum-Merit Scholarship Scheme",
        "hi": "राष्ट्रीय साधन-सह-योग्यता छात्रवृत्ति योजना",
        "url": "https://scholarships.gov.in/",
        "text_en": "The National Means-cum-Merit Scholarship Scheme is a scholarship programme intended to support meritorious students from economically weaker sections and encourage them to continue their studies, subject to eligibility and selection rules.",
        "text_hi": "राष्ट्रीय साधन-सह-योग्यता छात्रवृत्ति योजना आर्थिक रूप से कमजोर वर्गों के मेधावी विद्यार्थियों को सहायता देने और उन्हें अपनी पढ़ाई जारी रखने के लिए प्रोत्साहित करने वाली छात्रवृत्ति योजना है। यह पात्रता और चयन नियमों के अधीन है।"
    }
]


def load_existing_records():
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    original = load_existing_records()

    # Preserve the original dataset before making any changes.
    if not BACKUP_PATH.exists():
        shutil.copy2(CSV_PATH, BACKUP_PATH)
        print(f"Backup created: {BACKUP_PATH}")

    records = []
    seen = set()

    def add_record(record):
        key = (
            record["scheme_id"],
            record["lang"],
            record["section"]
        )
        if key in seen:
            return
        seen.add(key)
        records.append(record)

    # Preserve the original English records and add Hindi equivalents.
    for old in original:
        scheme_id = old["scheme_id"].strip()
        section = old["section"].strip()
        name_en = old["name_en"].strip()

        name_hi = {
            "PMKISAN": "प्रधानमंत्री किसान सम्मान निधि",
            "PMUY": "प्रधानमंत्री उज्ज्वला योजना"
        }.get(scheme_id, old["name_hi"].strip())

        old["name_hi"] = name_hi
        old["retrieved_on"] = TODAY
        add_record(old)

        hindi_text = EXISTING_HINDI.get((scheme_id, section))
        if hindi_text:
            add_record({
                "scheme_id": scheme_id,
                "name_en": name_en,
                "name_hi": name_hi,
                "lang": "hi",
                "section": section,
                "text": hindi_text,
                "source_url": old["source_url"],
                "retrieved_on": TODAY
            })

    # Add the other 18 schemes in both languages.
    for scheme in NEW_SCHEMES:
        for lang, text_key in [("en", "text_en"), ("hi", "text_hi")]:
            add_record({
                "scheme_id": scheme["id"],
                "name_en": scheme["en"],
                "name_hi": scheme["hi"],
                "lang": lang,
                "section": "overview",
                "text": scheme[text_key],
                "source_url": scheme["url"],
                "retrieved_on": TODAY
            })

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    # Validate the required scheme and language coverage.
    schemes = {}
    for row in records:
        schemes.setdefault(row["scheme_id"], set()).add(row["lang"])

    bilingual = [
        scheme_id for scheme_id, languages in schemes.items()
        if {"en", "hi"}.issubset(languages)
    ]

    print("\nDATASET BUILD COMPLETE")
    print("Total records:", len(records))
    print("Unique schemes:", len(schemes))
    print("Bilingual schemes:", len(bilingual))
    print("English records:", sum(r["lang"] == "en" for r in records))
    print("Hindi records:", sum(r["lang"] == "hi" for r in records))

    if len(schemes) != 20 or len(bilingual) != 20:
        raise ValueError("Dataset does not meet the 20-scheme bilingual target.")

    print("\nAll 20 schemes have English and Hindi records.")


if __name__ == "__main__":
    main()
