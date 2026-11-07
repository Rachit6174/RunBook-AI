import sys
from .agent import IncidentResponseAgent

def main():
    agent = IncidentResponseAgent()
    
    if len(sys.argv) > 1:
        # Allow passing incident text directly as a command-line argument
        incident = " ".join(sys.argv[1:])
    else:
        # Default interactive prompt if no argument given
        print("=== Incident Response Agent CLI ===")
        incident = input("Enter the security incident description: ").strip()
        if not incident:
            incident = "Unauthorized SSH login attempt detected from unknown IP."
            print(f"No input provided. Using default: '{incident}'")

    agent.handle_incident(incident)

if __name__ == "__main__":
    main()
