"""Controlled career directions for the current fourth-year elective catalogue."""

from __future__ import annotations

from typing import TypedDict


class CareerDirection(TypedDict):
    career_tag: str
    display_name: str
    description: str


ELECTIVE_CAREER_DIRECTIONS: dict[str, tuple[CareerDirection, ...]] = {
    "ELEN4001A": (
        {
            "career_tag": "rf_engineering",
            "display_name": "Radio-frequency engineering",
            "description": "Work involving RF circuits, microwave systems, antennas, and signal transmission.",
        },
        {
            "career_tag": "wireless_communications",
            "display_name": "Wireless communications engineering",
            "description": "Work on wireless links, radio networks, propagation, and communications infrastructure.",
        },
    ),
    "ELEN4003A": (
        {
            "career_tag": "high_voltage_engineering",
            "display_name": "High-voltage engineering",
            "description": "Work involving high-voltage equipment, insulation, testing, and electrical safety.",
        },
        {
            "career_tag": "power_systems_engineering",
            "display_name": "Power-systems engineering",
            "description": "Work on the generation, transmission, protection, and reliable delivery of electrical power.",
        },
    ),
    "ELEN4010A": (
        {
            "career_tag": "software_development",
            "display_name": "Software development",
            "description": "Work designing, implementing, testing, and maintaining software applications and services.",
        },
        {
            "career_tag": "systems_engineering",
            "display_name": "Software systems engineering",
            "description": "Work integrating software components into dependable technical systems.",
        },
    ),
    "ELEN4014A": (
        {
            "career_tag": "electrical_machines_engineering",
            "display_name": "Electrical-machines engineering",
            "description": "Work involving motors, generators, transformers, and electromechanical energy conversion.",
        },
        {
            "career_tag": "electric_drives_engineering",
            "display_name": "Electric-drives engineering",
            "description": "Work combining machines, power conversion, and control in industrial drive systems.",
        },
    ),
    "ELEN4016A": (
        {
            "career_tag": "control_engineering",
            "display_name": "Control engineering",
            "description": "Work designing and analysing controllers for dynamic engineering systems.",
        },
        {
            "career_tag": "automation_engineering",
            "display_name": "Automation engineering",
            "description": "Work applying control, instrumentation, and software to automated processes and equipment.",
        },
    ),
    "ELEN4017A": (
        {
            "career_tag": "network_engineering",
            "display_name": "Network engineering",
            "description": "Work designing, operating, securing, and troubleshooting computer networks.",
        },
        {
            "career_tag": "telecommunications_engineering",
            "display_name": "Telecommunications engineering",
            "description": "Work on communications networks, protocols, and connected infrastructure.",
        },
    ),
    "ELEN4018A": (
        {
            "career_tag": "power_systems_engineering",
            "display_name": "Power-systems engineering",
            "description": "Work on electrical generation, transmission, distribution, protection, and grid reliability.",
        },
        {
            "career_tag": "grid_planning",
            "display_name": "Grid planning and operations",
            "description": "Work analysing electricity networks and planning their safe, reliable operation and expansion.",
        },
    ),
    "ELEN4020A": (
        {
            "career_tag": "data_engineering",
            "display_name": "Data engineering",
            "description": "Work building reliable systems and pipelines for collecting, processing, and serving data.",
        },
        {
            "career_tag": "data_science",
            "display_name": "Data science",
            "description": "Work using data analysis, statistical modelling, and computing to support decisions.",
        },
    ),
    "ELEN4022A": (
        {
            "career_tag": "quantum_software",
            "display_name": "Quantum software development",
            "description": "Work developing and testing software workflows for quantum-computing platforms.",
        },
        {
            "career_tag": "quantum_computing_research",
            "display_name": "Quantum-computing research",
            "description": "Research-oriented work in quantum algorithms and systems, commonly requiring postgraduate study.",
        },
    ),
    "ELEN4023A": (
        {
            "career_tag": "renewable_energy_engineering",
            "display_name": "Renewable-energy engineering",
            "description": "Work involving renewable generation technologies and their integration into energy systems.",
        },
        {
            "career_tag": "energy_systems_engineering",
            "display_name": "Energy-systems engineering",
            "description": "Work analysing and designing efficient, reliable, and sustainable energy systems.",
        },
    ),
    "ELEN4024A": (
        {
            "career_tag": "cybersecurity_engineering",
            "display_name": "Cybersecurity engineering",
            "description": "Work designing and maintaining systems that resist security threats and attacks.",
        },
        {
            "career_tag": "secure_software_engineering",
            "display_name": "Secure-software engineering",
            "description": "Work building software with security controls throughout its design and development lifecycle.",
        },
    ),
    "ELEN4025A": (
        {
            "career_tag": "ml_engineering",
            "display_name": "Machine-learning engineering",
            "description": "Work developing, evaluating, and deploying machine-learning systems.",
        },
        {
            "career_tag": "data_science",
            "display_name": "Data science",
            "description": "Work involving data analysis, statistical modelling, and evidence-based decisions.",
        },
    ),
}

