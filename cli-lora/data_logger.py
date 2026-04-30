import serial
import csv
import time
import re

def capture_and_save_data(num_packets: int, port: str = "COM5", baudrate: int = 9600, csv_file: str = "data_log.csv"):
    """
    Capture les données du port série et les sauvegarde en CSV
    
    Args:
        num_packets: Nombre de paquets à capturer
        port: Port série (ex: COM4, COM5)
        baudrate: Vitesse de transmission (9600 par défaut)
        csv_file: Nom du fichier CSV de sortie
    """
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=1)
    data_list = []
    current_packet = {}
    packet_count = 0
    
    try:
        print(f"🔄 Écoute sur {port}... (capture de {num_packets} paquets)")
        print(f"   Baudrate: {baudrate}, Fichier: {csv_file}\n")
        
        while packet_count < num_packets:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if not line or line.startswith("["):
                    continue
                
                # Parse RSSI
                if "RSSI:" in line:
                    try:
                        rssi = float(re.search(r'-?\d+\.?\d*', line).group())
                        current_packet['RSSI'] = rssi
                    except:
                        pass
                
                # Parse SNR
                elif "SNR:" in line:
                    try:
                        snr = float(re.search(r'-?\d+\.?\d*', line).group())
                        current_packet['SNR'] = snr
                    except:
                        pass
                
                # Parse Frequency Error
                elif "Frequency Error:" in line:
                    try:
                        freq_err = float(re.search(r'-?\d+\.?\d*', line).group())
                        current_packet['Frequency Error'] = freq_err
                        
                        # Paquet complet: sauvegarder
                        if len(current_packet) == 3:
                            current_packet['n°packet'] = packet_count + 1
                            data_list.append(current_packet)
                            packet_count += 1
                            print(f"  ✓ Paquet {current_packet['n°packet']}: RSSI={current_packet['RSSI']} SNR={current_packet['SNR']} FE={current_packet['Frequency Error']}")
                            current_packet = {}
                    except:
                        pass
    
    except KeyboardInterrupt:
        print("\n⚠️  Capture arrêtée par l'utilisateur")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    finally:
        ser.close()
        
        # Sauvegarder en CSV
        if data_list:
            save_to_csv(data_list, csv_file)
        else:
            print("❌ Aucune donnée capturée")

def save_to_csv(data_list, filename: str = "data_log.csv"):
    """Sauvegarde les données en CSV"""
    try:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['n°packet', 'RSSI', 'SNR', 'Frequency Error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(data_list)
        
        print(f"\n✅ CSV généré: {filename}")
        print(f"   {len(data_list)} paquets enregistrés")
    
    except Exception as e:
        print(f"❌ Erreur sauvegarde CSV: {e}")