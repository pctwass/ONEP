import os
import subprocess
import sys
import dependency_resolver
from utils.logging import logger
from main import launch, start, stop

CONSOLE_COMMANDS = ["LAUNCH", "START", "STOP", "EXIT"]


class ConsoleInterface():
    def run_console(self):
        print("Welcome to ONEP!")

        exit = False
        while not exit:
            self.print_menu()
            command = self.get_user_input()
            exit = self.execute_command(command)


    def print_menu(self):
        print("Select one of the following commands:")
        for i, command in enumerate(CONSOLE_COMMANDS):
            print(f"{i+1}. {command}")

    
    def get_user_input(self):
        while True:
            user_input = input("Enter your command: ").strip().upper()
            if user_input in CONSOLE_COMMANDS:
                return user_input
            else:
                print("Invalid command. Please try again.")


    # returns True to exit the application
    def execute_command(self, command):
        match command:
            case "LAUNCH": 
                print("Launching ONEP, this may take a moment.")
                launch()
            case "START":
                print("Starting projector.")
                start()
            case "STOP":
                print("Stopping projector.")
                stop()
            case "EXIT":
                return True
        return False


def main():
    script_path = os.path.abspath(__file__)
    command = f'start cmd /k python {script_path} --run-interface'
    subprocess.run(command, shell=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--run-interface':
        interface = ConsoleInterface()
        interface.run_console()
    else:
        main()