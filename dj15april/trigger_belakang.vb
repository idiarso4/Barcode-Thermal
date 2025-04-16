Imports System.IO.Ports

Public Class RelayControlForm
    ' Declare the SerialPort object
    Private WithEvents serialPort As New SerialPort()

    ' Form Load event
    Private Sub RelayControlForm_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        ' Configure the serial port
        serialPort.PortName = "COM3" ' Replace with your actual COM port
        serialPort.BaudRate = 9600

        Try
            ' Open the serial port
            serialPort.Open()
            MessageBox.Show($"Connected to {serialPort.PortName} at {serialPort.BaudRate} baud.")
        Catch ex As Exception
            MessageBox.Show($"Error: {ex.Message}")
        End Try
    End Sub

    ' Button Click event to turn the relay ON
    Private Sub btnTurnOn_Click(sender As Object, e As EventArgs) Handles btnTurnOn.Click
        Try
            ' Send the "ON" command to the Arduino
            serialPort.WriteLine("ON")
            MessageBox.Show("Relay turned ON.")
        Catch ex As Exception
            MessageBox.Show($"Error: {ex.Message}")
        End Try
    End Sub

    ' Button Click event to turn the relay OFF
    Private Sub btnTurnOff_Click(sender As Object, e As EventArgs) Handles btnTurnOff.Click
        Try
            ' Send the "OFF" command to the Arduino
            serialPort.WriteLine("OFF")
            MessageBox.Show("Relay turned OFF.")
        Catch ex As Exception
            MessageBox.Show($"Error: {ex.Message}")
        End Try
    End Sub

    ' Handle DataReceived event (optional)
    Private Sub SerialPort_DataReceived(sender As Object, e As SerialDataReceivedEventArgs) Handles serialPort.DataReceived
        ' Read the response from the Arduino
        Dim response As String = serialPort.ReadLine().Trim()

        ' Display the response in a message box (optional)
        MessageBox.Show($"Arduino says: {response}")
    End Sub

    ' Form Closing event
    Private Sub RelayControlForm_FormClosing(sender As Object, e As FormClosingEventArgs) Handles MyBase.FormClosing
        ' Close the serial port when the form is closed
        If serialPort.IsOpen Then
            serialPort.Close()
        End If
    End Sub
End Class
