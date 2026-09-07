"""
create_sample_docs.py
Generates sample documents across two distinct domains for the
AI-Based Knowledge Retrieval Platform demonstration.

Domain 1: Computer Science / Operating Systems (PDF + CSV)
Domain 2: Artificial Intelligence (DOCX + TXT)

Run this script once to produce the sample_docs directory:
    python create_sample_docs.py
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import docx
import csv


SAMPLE_DIR = Path("data/sample_docs")
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DOMAIN 1: Operating Systems PDF
# =============================================================================

def create_os_pdf():
    path = SAMPLE_DIR / "Operating_Systems.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=20, spaceAfter=20, alignment=TA_CENTER)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, spaceAfter=10, spaceBefore=14)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=8, spaceBefore=10)
    body = ParagraphStyle("Body2", parent=styles["Normal"], fontSize=10.5, leading=16, spaceAfter=8)

    story = []

    # --- Page 1: Introduction ---
    story.append(Paragraph("Operating Systems: Core Concepts", title_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Chapter 1: Introduction to Operating Systems", h1))
    story.append(Paragraph(
        "An operating system (OS) is a system software that manages computer hardware, software resources, "
        "and provides common services for computer programs. It acts as an intermediary between users and "
        "the computer hardware. Major functions include process management, memory management, file system "
        "management, and device control.", body))
    story.append(Paragraph(
        "The operating system provides a layer of abstraction that shields application programs from the "
        "complexity of the underlying hardware. Without an operating system, each application would need "
        "to implement its own hardware-level interactions, making software development considerably more difficult.", body))

    story.append(Paragraph("Types of Operating Systems", h2))
    story.append(Paragraph(
        "Batch Operating Systems process jobs without user interaction. Multiprogramming OS allows multiple "
        "programs to reside in memory simultaneously. Time-Sharing OS allocates CPU time to multiple users. "
        "Real-Time OS is used in systems where time constraints are critical, such as aircraft control or "
        "medical imaging devices. Distributed OS manages a group of distinct computers and presents them as "
        "a single coherent system.", body))

    story.append(PageBreak())

    # --- Page 2: Process Management ---
    story.append(Paragraph("Chapter 2: Process Management", h1))
    story.append(Paragraph(
        "A process is a program in execution. It includes the program code, current activity (program counter), "
        "a stack containing temporary data, and a data section containing global variables. The operating system "
        "manages processes by scheduling them on the CPU.", body))
    story.append(Paragraph("Process States", h2))
    story.append(Paragraph(
        "A process passes through several states during its lifetime. In the New state, the process is being "
        "created. In the Running state, instructions are being executed. In the Waiting state, the process is "
        "waiting for an event such as I/O completion. In the Ready state, the process is waiting to be assigned "
        "to a processor. In the Terminated state, the process has finished execution.", body))
    story.append(Paragraph("CPU Scheduling", h2))
    story.append(Paragraph(
        "CPU scheduling is the process of determining which process in the ready queue is allocated the CPU. "
        "Common scheduling algorithms include First-Come First-Served (FCFS), Shortest Job First (SJF), "
        "Round Robin (RR), and Priority Scheduling. Round Robin is widely used in time-sharing systems "
        "because it gives every process a fair share of CPU time.", body))

    story.append(PageBreak())

    # --- Page 3: Memory Management ---
    story.append(Paragraph("Chapter 3: Memory Management", h1))
    story.append(Paragraph(
        "Memory management is one of the most critical responsibilities of an operating system. The OS must "
        "keep track of which parts of memory are in use and which are free. When a process requests memory, "
        "the OS must allocate it; when the process finishes, the OS must reclaim it.", body))
    story.append(Paragraph("Contiguous Memory Allocation", h2))
    story.append(Paragraph(
        "In contiguous memory allocation, each process is allocated a single contiguous section of memory. "
        "This can lead to fragmentation over time. External fragmentation occurs when there is enough total "
        "free memory but it is not contiguous. Internal fragmentation occurs when allocated memory is larger "
        "than what is needed.", body))
    story.append(Paragraph("Paging", h2))
    story.append(Paragraph(
        "Paging is a memory management scheme that eliminates the requirement for contiguous allocation of physical "
        "memory. Physical memory is divided into fixed-sized blocks called frames. Logical memory is divided into "
        "blocks of the same size called pages. When a process executes, its pages are loaded into available frames. "
        "The OS maintains a page table for each process that maps logical page numbers to physical frame numbers.", body))

    story.append(PageBreak())

    # --- Page 4: Virtual Memory ---
    story.append(Paragraph("Chapter 4: Virtual Memory", h1))
    story.append(Paragraph(
        "Virtual memory is a memory management technique that provides an idealized abstraction of the storage "
        "resources actually available on a given machine. It creates the illusion for users of a very large "
        "primary memory. Virtual memory allows a computer to execute programs that are larger than the available "
        "physical RAM by using secondary storage as an extension of main memory.", body))
    story.append(Paragraph(
        "The key benefit of virtual memory is that processes do not need to be entirely in physical memory to "
        "execute. Only the portions of a process that are currently being used need to reside in RAM. The remaining "
        "portions can be stored on disk and brought in only when needed.", body))
    story.append(Paragraph("Demand Paging", h2))
    story.append(Paragraph(
        "Demand paging is a technique used in virtual memory systems where pages are loaded into physical memory "
        "only when they are needed (demanded), rather than loading the entire program at once. This approach saves "
        "memory and time because unused pages are never loaded. When a page is needed but not in memory, a page "
        "fault occurs, triggering the OS to load that page from disk.", body))
    story.append(Paragraph("Page Faults", h2))
    story.append(Paragraph(
        "A page fault is a type of interrupt raised by hardware when a running program accesses a memory page "
        "that is mapped in the virtual address space but not loaded into physical memory. When a page fault "
        "occurs, the operating system must handle it by finding a free frame in physical memory, loading the "
        "required page from secondary storage, and then resuming the interrupted instruction.", body))

    story.append(PageBreak())

    # --- Page 5: Page Replacement ---
    story.append(Paragraph("Chapter 5: Page Replacement Algorithms", h1))
    story.append(Paragraph(
        "When a page fault occurs and all frames in physical memory are occupied, the OS must replace an "
        "existing page to make room for the new one. The algorithm used to decide which page to replace is "
        "called a page replacement algorithm. Choosing poorly can significantly degrade performance.", body))
    story.append(Paragraph("FIFO Page Replacement", h2))
    story.append(Paragraph(
        "First-In-First-Out (FIFO) is the simplest page replacement algorithm. In FIFO, the oldest page "
        "in memory is replaced first. While simple to implement, FIFO suffers from Belady's anomaly, "
        "where increasing the number of frames can paradoxically increase the page fault rate.", body))
    story.append(Paragraph("LRU Page Replacement", h2))
    story.append(Paragraph(
        "Least Recently Used (LRU) replacement replaces the page that has not been used for the longest "
        "period of time. LRU is based on the principle of temporal locality: if a page has not been used "
        "recently, it is unlikely to be used in the near future. LRU is more accurate than FIFO but is "
        "more complex to implement due to tracking usage history.", body))
    story.append(Paragraph("Thrashing", h2))
    story.append(Paragraph(
        "Thrashing is a condition where excessive paging activity degrades system performance significantly. "
        "When a process does not have enough frames to support its active working set, page faults occur "
        "at a very high rate. The OS spends more time handling page faults than executing actual process "
        "instructions. Thrashing can be detected by monitoring CPU utilization: if it drops sharply, "
        "thrashing is likely occurring.", body))

    story.append(PageBreak())

    # --- Page 6: File Systems ---
    story.append(Paragraph("Chapter 6: File Systems", h1))
    story.append(Paragraph(
        "A file system controls how data is stored and retrieved on storage devices. A file is a named "
        "collection of related data stored on secondary storage. File systems define the format and structure "
        "for storing, organizing, and accessing data on disk.", body))
    story.append(Paragraph("File Attributes", h2))
    story.append(Paragraph(
        "Files have attributes including name, type, location (pointer to file on device), size, protection "
        "(access rights), timestamps (creation, modification), and owner information. These attributes are "
        "maintained in the directory structure.", body))
    story.append(Paragraph("Directory Structures", h2))
    story.append(Paragraph(
        "Directories organize files within the file system. Single-level directories contain all files in "
        "a flat structure. Two-level directories have a separate directory for each user. Tree-structured "
        "directories allow arbitrary levels of subdirectories. Modern operating systems typically support "
        "tree-structured or acyclic graph directories.", body))

    doc.build(story)
    print(f"[SAMPLE] Created: {path}")


# =============================================================================
# DOMAIN 1: Student Records CSV
# =============================================================================

def create_students_csv():
    path = SAMPLE_DIR / "students.csv"
    students = [
        ["RollNo", "Name", "Department", "CGPA", "Year", "Project_Domain", "Status"],
        ["CS001", "Ravi Kumar",    "CSE",  "8.7", "3rd", "Machine Learning",     "Active"],
        ["CS002", "Priya Sharma",  "CSE",  "9.1", "3rd", "Web Development",      "Active"],
        ["CS003", "Arjun Nair",    "CSE",  "7.8", "4th", "Data Science",         "Active"],
        ["EC001", "Sneha Patel",   "ECE",  "8.3", "3rd", "Embedded Systems",     "Active"],
        ["EC002", "Mohammed Ali",  "ECE",  "7.5", "4th", "Signal Processing",    "Completed"],
        ["IT001", "Ananya Singh",  "IT",   "8.9", "3rd", "Cybersecurity",        "Active"],
        ["IT002", "Rahul Gupta",   "IT",   "7.2", "2nd", "Cloud Computing",      "Active"],
        ["ME001", "Divya Menon",   "MECH", "6.8", "4th", "Robotics",             "Completed"],
        ["ME002", "Karthik Iyer",  "MECH", "7.9", "3rd", "IoT Systems",          "Active"],
        ["CS004", "Lavanya Bose",  "CSE",  "9.4", "4th", "Natural Language Processing", "Active"],
        ["CS005", "Vikram Reddy",  "CSE",  "8.1", "2nd", "Computer Vision",      "Active"],
        ["IT003", "Meera Joshi",   "IT",   "8.6", "3rd", "Blockchain Technology","Active"],
        ["EC003", "Suresh Pillai", "ECE",  "7.1", "4th", "VLSI Design",          "Completed"],
        ["CS006", "Pooja Verma",   "CSE",  "9.0", "3rd", "Deep Learning",        "Active"],
        ["IT004", "Arun Krishnan", "IT",   "7.8", "4th", "DevOps and CI/CD",     "Completed"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(students)
    print(f"[SAMPLE] Created: {path}")


# =============================================================================
# DOMAIN 2: Artificial Intelligence DOCX
# =============================================================================

def create_ai_docx():
    path = SAMPLE_DIR / "Artificial_Intelligence.docx"
    doc = docx.Document()

    # Document title
    title = doc.add_heading("Introduction to Artificial Intelligence and Machine Learning", 0)
    title.alignment = 1

    doc.add_paragraph(
        "This document provides a comprehensive overview of Artificial Intelligence, Machine Learning, "
        "Deep Learning, Neural Networks, and modern architectures including Transformers and "
        "Retrieval-Augmented Generation (RAG)."
    )
    doc.add_paragraph("")

    # Chapter 1
    doc.add_heading("Chapter 1: Foundations of Artificial Intelligence", 1)
    doc.add_paragraph(
        "Artificial Intelligence (AI) is the simulation of human intelligence processes by computer systems. "
        "These processes include learning (the acquisition of information and rules for using the information), "
        "reasoning (using the rules to reach approximate or definite conclusions), and self-correction. "
        "AI applications include expert systems, natural language processing, speech recognition, and machine vision."
    )
    doc.add_heading("Machine Learning vs. Traditional Programming", 2)
    doc.add_paragraph(
        "In traditional programming, a human explicitly programs rules that define how the system behaves. "
        "In Machine Learning, the system learns these rules automatically from data. A Machine Learning model "
        "is trained on examples and generalizes its learning to new, unseen data. Supervised learning uses "
        "labeled training data. Unsupervised learning finds patterns in unlabeled data. Reinforcement learning "
        "trains agents by rewarding correct actions and penalizing incorrect ones."
    )

    # Chapter 2
    doc.add_heading("Chapter 2: Neural Networks and Deep Learning", 1)
    doc.add_paragraph(
        "Neural networks are computational models loosely inspired by the structure of the human brain. "
        "They consist of layers of interconnected nodes (neurons). The input layer receives raw data. "
        "Hidden layers transform inputs through learned weight matrices. The output layer produces predictions."
    )
    doc.add_heading("Activation Functions", 2)
    doc.add_paragraph(
        "Activation functions introduce non-linearity into the network, enabling it to learn complex patterns. "
        "The Sigmoid function outputs values between 0 and 1 and is used in binary classification. "
        "The ReLU (Rectified Linear Unit) function sets negative values to zero and is widely used in hidden "
        "layers because it avoids the vanishing gradient problem. The Softmax function normalizes outputs into "
        "a probability distribution over multiple classes."
    )
    doc.add_heading("Backpropagation", 2)
    doc.add_paragraph(
        "Backpropagation is the algorithm used to train neural networks by computing gradients of the loss "
        "function with respect to each weight using the chain rule of calculus. Gradients are propagated "
        "backwards through the network from output to input layers, and weights are updated using gradient "
        "descent optimization."
    )

    # Chapter 3
    doc.add_heading("Chapter 3: The Transformer Architecture", 1)
    doc.add_paragraph(
        "The Transformer is a deep learning architecture introduced in 2017 in the paper 'Attention is All "
        "You Need' by Vaswani et al. It replaced recurrent architectures for many NLP tasks and became the "
        "foundation for modern large language models. The Transformer processes input sequences in parallel "
        "rather than sequentially, which significantly improves training efficiency."
    )
    doc.add_heading("The Attention Mechanism", 2)
    doc.add_paragraph(
        "The attention mechanism allows a model to dynamically focus on different parts of the input sequence "
        "when generating each output token. Given a set of queries, keys, and values, attention computes a "
        "weighted sum of values, where the weights are determined by the similarity between queries and keys. "
        "Self-attention allows each position in the sequence to attend to all other positions, capturing "
        "long-range dependencies that recurrent networks struggle with."
    )
    doc.add_heading("Multi-Head Attention", 2)
    doc.add_paragraph(
        "Multi-head attention runs the attention mechanism multiple times in parallel, each with different "
        "learned projections. The outputs are concatenated and projected to produce the final result. "
        "This allows the model to attend to information from different representation subspaces simultaneously."
    )

    # Chapter 4
    doc.add_heading("Chapter 4: Large Language Models (LLMs)", 1)
    doc.add_paragraph(
        "Large Language Models (LLMs) are Transformer-based neural networks trained on massive text corpora "
        "to predict the next token in a sequence. Examples include GPT-4, BERT, LLaMA, and Gemini. "
        "LLMs can generate coherent text, answer questions, translate languages, write code, and summarize documents. "
        "They are fine-tuned on specific tasks using supervised or reinforcement learning from human feedback (RLHF)."
    )
    doc.add_heading("Limitations of LLMs", 2)
    doc.add_paragraph(
        "LLMs have several significant limitations. They have a knowledge cutoff date and cannot access real-time "
        "information. They can hallucinate, generating factually incorrect but plausible-sounding content. "
        "They may not have access to private or domain-specific documents. Context window limitations restrict "
        "how much text a model can process at once."
    )

    # Chapter 5
    doc.add_heading("Chapter 5: Retrieval-Augmented Generation (RAG)", 1)
    doc.add_paragraph(
        "Retrieval-Augmented Generation (RAG) is an AI framework that combines a retrieval system with a "
        "generative language model. Instead of relying solely on memorized training data, RAG first retrieves "
        "relevant document chunks from a knowledge base using semantic similarity search, then uses those "
        "retrieved documents as context for the language model to generate a grounded, accurate answer."
    )
    doc.add_heading("RAG Pipeline Components", 2)
    doc.add_paragraph(
        "A RAG pipeline consists of several stages. During indexing, documents are split into chunks, "
        "embedded into dense vector representations, and stored in a vector database such as FAISS, Pinecone, "
        "or Chroma. During query time, the user's question is embedded using the same model, and cosine "
        "similarity search retrieves the most relevant chunks. These chunks are then passed as context to "
        "the language model to generate a grounded answer."
    )
    doc.add_heading("Why RAG is Important", 2)
    doc.add_paragraph(
        "RAG addresses the key limitations of standalone LLMs. By grounding answers in retrieved documents, "
        "RAG reduces hallucination and improves factual accuracy. It enables LLMs to access domain-specific "
        "or up-to-date information without retraining the model. RAG is particularly valuable for enterprise "
        "applications where users need reliable answers from private document collections, such as "
        "legal databases, scientific literature, corporate knowledge bases, and educational content."
    )

    doc.save(path)
    print(f"[SAMPLE] Created: {path}")


# =============================================================================
# DOMAIN 2: Cybersecurity TXT
# =============================================================================

def create_cybersecurity_txt():
    path = SAMPLE_DIR / "Cybersecurity_Basics.txt"
    content = """INTRODUCTION TO CYBERSECURITY
==============================

Cybersecurity refers to the practice of protecting systems, networks, and programs from digital attacks. These cyberattacks are usually aimed at accessing, changing, or destroying sensitive information, extorting money from users, or interrupting normal business processes.

---

CHAPTER 1: CRYPTOGRAPHY FUNDAMENTALS
--------------------------------------

Cryptography is the practice and study of techniques for secure communication in the presence of adversarial behavior. It is the foundation of data security in digital systems.

Symmetric Key Cryptography:
In symmetric encryption, the same key is used for both encryption and decryption. Examples include AES (Advanced Encryption Standard) and DES (Data Encryption Standard). Symmetric encryption is fast and efficient, making it suitable for encrypting large amounts of data. The main challenge is securely distributing the shared key between communicating parties.

Asymmetric Key Cryptography (Public Key Cryptography):
Asymmetric encryption uses a pair of mathematically related keys: a public key for encryption and a private key for decryption. RSA and ECC (Elliptic Curve Cryptography) are common asymmetric algorithms. Public key cryptography solves the key distribution problem: anyone can encrypt a message using a public key, but only the holder of the corresponding private key can decrypt it. This is the basis for HTTPS, digital signatures, and certificate authorities.

Hashing:
A hash function takes input data and produces a fixed-size output (hash or digest). Hashing is one-way: you cannot derive the original data from a hash. SHA-256 is a widely used cryptographic hash function. Hashing is used for password storage, data integrity verification, and digital signatures.

---

CHAPTER 2: NETWORK SECURITY
-----------------------------

Network security involves policies and practices to prevent unauthorized access, misuse, modification, or denial of network resources.

Firewalls:
A firewall is a network security system that monitors and controls incoming and outgoing network traffic based on predetermined security rules. Firewalls can be hardware-based, software-based, or cloud-based. A packet-filtering firewall inspects individual packets and allows or denies them based on rules. A stateful firewall tracks the state of active connections and makes decisions based on the context of traffic, not just individual packets.

Intrusion Detection Systems (IDS) and Intrusion Prevention Systems (IPS):
An IDS monitors network traffic for suspicious activity and issues alerts when potential attacks are detected. An IPS actively blocks identified threats. Together, IDS/IPS systems form a critical layer of defense in enterprise networks.

Virtual Private Networks (VPN):
A VPN extends a private network across a public network, enabling users to send and receive data as if their devices were directly connected to the private network. VPNs use encryption to protect data in transit. Common VPN protocols include OpenVPN, WireGuard, and IPSec.

---

CHAPTER 3: ZERO TRUST ARCHITECTURE
-------------------------------------

Zero Trust is a security model based on the principle of "never trust, always verify." Unlike traditional perimeter-based security models that trust everything inside the network, Zero Trust assumes that threats can exist both outside and inside the network perimeter.

Core Principles of Zero Trust:
1. Verify explicitly: Always authenticate and authorize based on all available data points including identity, location, device health, and data classification.
2. Least privilege access: Limit user access with Just-In-Time and Just-Enough-Access, risk-based adaptive policies, and data protection.
3. Assume breach: Minimize blast radius, segment access, verify end-to-end encryption, and use analytics to detect anomalies.

Zero Trust Implementation:
Implementing Zero Trust requires strong identity management (using Multi-Factor Authentication), microsegmentation of the network, continuous monitoring of user behavior, and encryption of data both in transit and at rest. Zero Trust is increasingly adopted by organizations to secure cloud-native applications and remote workforces.

---

CHAPTER 4: COMMON ATTACK VECTORS
-----------------------------------

Phishing:
Phishing is a social engineering attack where attackers impersonate trusted entities to trick users into revealing credentials, financial information, or installing malware. Spear phishing targets specific individuals using personalized information.

SQL Injection:
SQL injection is a code injection technique used to attack data-driven applications by inserting malicious SQL statements into entry fields. This can allow attackers to read, modify, or delete database contents. Prevention involves parameterized queries and input validation.

Man-in-the-Middle (MITM) Attack:
In a MITM attack, the attacker secretly intercepts and possibly alters communications between two parties who believe they are communicating directly with each other. Using HTTPS and certificate pinning helps mitigate MITM attacks.

Denial-of-Service (DoS) and Distributed Denial-of-Service (DDoS):
DoS attacks aim to make a service unavailable by overwhelming it with traffic. DDoS attacks use multiple compromised systems to launch coordinated floods of traffic. Mitigation involves rate limiting, traffic filtering, and CDN-based protection.

---

CHAPTER 5: SECURITY BEST PRACTICES
-------------------------------------

1. Keep software and systems updated to patch known vulnerabilities.
2. Use strong, unique passwords for every account and store them in a password manager.
3. Enable Multi-Factor Authentication (MFA) wherever possible.
4. Encrypt sensitive data both in transit (TLS/HTTPS) and at rest.
5. Regularly back up critical data and test restoration procedures.
6. Follow the Principle of Least Privilege: grant users only the access they need.
7. Conduct regular security audits and penetration testing.
8. Train employees in security awareness to recognize phishing and social engineering.
9. Monitor systems with logging and intrusion detection tools.
10. Develop and maintain an incident response plan.
"""
    path.write_text(content, encoding="utf-8")
    print(f"[SAMPLE] Created: {path}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("[SAMPLE] Generating sample documents for demonstration...")
    create_os_pdf()
    create_students_csv()
    create_ai_docx()
    create_cybersecurity_txt()
    print("[SAMPLE] All sample documents created successfully in:", SAMPLE_DIR.resolve())
