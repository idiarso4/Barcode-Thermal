import configparser

config = configparser.ConfigParser()

config['camera'] = {
    'type': 'dummy',
    'ip': '192.168.2.20',
    'port': '554',
    'username': 'admin',
    'password': '@dminparkir',
    'protocol': 'rtsp'
}

config['button'] = {
    'type': 'serial',
    'port': 'COM7',
    'baudrate': '9600'
}

config['printer'] = {
    'type': 'escpos',
    'vendor_id': '0x0483',
    'product_id': '0x5740'
}

config['database'] = {
    'dbname': 'parkir2',
    'user': 'postgres',
    'password': 'postgres',
    'host': '192.168.2.6',
    'port': '5432'
}

config['image'] = {
    'width': '1920',
    'height': '1080',
    'preview_width': '960',
    'preview_height': '540',
    'quality': '95'
}

config['storage'] = {
    'capture_dir': 'capture_images',
    'min_free_space_gb': '1'
}

config['system'] = {
    'log_file': 'parking.log',
    'counter_file': 'counter.txt',
    'admin_password': '1q2w3e4r5t66'
}

with open('config.ini', 'w') as configfile:
    config.write(configfile) 