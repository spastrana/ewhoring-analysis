from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.Qt import *

import pickle
import sys
import os
from datetime import datetime
import argparse



currentFile=0

possibleLanguages=['English','German','French','Spanish','Italian','Portuguese','Non-Latin','Other']
possiblePlatforms=['Missing','Amazon','Paypal','Bitcoin','Cash','Other']
possibleShots=['Missing','Dashboard','Email','Partial','Mobile-APP','Mobile-SMS','Mobile-Other','Other']
possibleClassesNoProof=['Conversation','Virtual Cam','Purchase','Dispute','Other']
possibleCurrencies=['Missing','USD','EUR','British Pound','Canadian Dollar','Other']

class Example(QWidget):
    
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
    def initUI(self):      
        global currentFile
        main = QGridLayout(self)
        imageArea=QVBoxLayout(self)
        dataArea=QVBoxLayout(self)
    

        self.labelCounter=QLabel()
        
        self.labelCounter.setText("Image %s of %s"%(currentFile+1,len(filePaths)))
        self.labelName=QLabel()
        self.labelName.setText("Year %s"%fileNames[currentFile][:4])

        self.lbl = QLabel(self)
        self.lbl.setScaledContents(True);
        self.lbl.setPixmap(QPixmap(filePaths[currentFile]))
        self.lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored);

        buttonsArea=QHBoxLayout()
        self.nextButton = QPushButton('Next Image   ', self)
        self.nextButton.clicked[bool].connect(self.nextImage)
        self.nextButton.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.previousButton = QPushButton('Previous Image', self)
        self.previousButton.clicked[bool].connect(self.previousImage)
        self.previousButton.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        buttonsArea.addWidget(self.previousButton)
        buttonsArea.addWidget(self.nextButton)
        
        self.labelNotes=QLabel()
        self.labelNotes.setText("Extra notes:")
        self.labelNotes.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.notes=QTextEdit()
        self.notes.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))

        languageArea=QGridLayout(self)
        self.labelLanguage=QLabel()
        self.labelLanguage.setText("Language:")
        self.labelLanguage.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboLanguage = QComboBox(self)
        self.comboLanguage.addItems(possibleLanguages)
        self.comboLanguage.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelOtherLanguage=QLabel()
        self.labelOtherLanguage.setText("If other, please specify:")
        self.labelOtherLanguage.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textOtherLanguage = QLineEdit()
        self.textOtherLanguage.setReadOnly(True)
        self.textOtherLanguage.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboLanguage.currentIndexChanged.connect(self.comboLanguageChange)
        languageArea.addWidget(self.labelLanguage,1,1)
        languageArea.addWidget(self.labelOtherLanguage,1,2)
        languageArea.addWidget(self.comboLanguage,2,1)
        languageArea.addWidget(self.textOtherLanguage,2,2)

        noProofArea=QGridLayout(self)
        self.checkNoProof = QCheckBox("Check if this is not a proof of earning")
        self.checkNoProof.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.checkNoProof.toggled.connect(self.noProofChecked)
        self.labelNoProof=QLabel()
        self.labelNoProof.setText("Please select a class from below:")
        self.labelNoProof.setStyleSheet("QLabel {color : gray; }")
        self.labelNoProof.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboNoProof = QComboBox(self)
        self.comboNoProof.addItems(possibleClassesNoProof)
        self.comboNoProof.setEnabled(False)
        self.comboNoProof.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelOtherClass=QLabel()
        self.labelOtherClass.setStyleSheet("QLabel {color : gray; }")
        self.labelOtherClass.setText("If other, please specify:")
        self.labelOtherClass.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textOtherClass = QLineEdit()
        self.textOtherClass.setReadOnly(True)
        self.textOtherClass.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboNoProof.currentIndexChanged.connect(self.comboNoProofChange)
        noProofArea.addWidget(self.labelNoProof,1,1)
        noProofArea.addWidget(self.labelOtherClass,1,2)
        noProofArea.addWidget(self.comboNoProof,2,1)
        noProofArea.addWidget(self.textOtherClass,2,2)

        self.labelAmount=QLabel()
        self.labelAmount.setText("Total amount")
        self.labelAmount.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textAmount = QLineEdit()
        self.textAmount.setValidator(QDoubleValidator())
        self.textAmount.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))


        transactionsArea=QGridLayout(self)
        self.checkTransactions = QCheckBox("Transactions?")
        self.checkTransactions.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.checkTransactions.toggled.connect(self.transactionsChecked)
        self.labelNumTransactions=QLabel()
        self.labelNumTransactions.setText("Num transactions")
        self.labelNumTransactions.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.numTransactions = QLineEdit()
        self.numTransactions.setValidator(QIntValidator())
        self.numTransactions.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelTransactionAmount=QLabel()
        self.labelTransactionAmount.setText("Sum amount")
        self.labelTransactionAmount.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textTransactionAmount = QLineEdit()
        self.textTransactionAmount.setValidator(QDoubleValidator())
        self.textTransactionAmount.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        
        self.labelTransactionSpan=QLabel()
        self.labelTransactionSpan.setText("Period (dd/mm/aa)")
        self.labelTransactionSpan.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelFrom=QLabel()
        self.labelFrom.setText("From")
        self.labelFrom.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textFrom = QLineEdit()
        self.textFrom.setValidator(QRegExpValidator(QRegExp("[0-9]{2}/[0-9]{2}/[0-9]{2}")))
        self.textFrom.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))

        self.labelTo=QLabel()
        self.labelTo.setText("To")
        self.labelTo.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textTo = QLineEdit()
        self.textTo.setValidator(QRegExpValidator(QRegExp("[0-9]{2}/[0-9]{2}/[0-9]{2}")))
        self.textTo.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))        
        transactionsArea.addWidget(self.checkTransactions,1,2)
        transactionsArea.addWidget(self.labelNumTransactions,2,1)
        transactionsArea.addWidget(self.numTransactions,2,2)
        transactionsArea.addWidget(self.labelTransactionAmount,3,1)
        transactionsArea.addWidget(self.textTransactionAmount,3,2)
        transactionsArea.addWidget(self.labelTransactionSpan,4,1)
        transactionsArea.addWidget(self.labelFrom,5,1)
        transactionsArea.addWidget(self.textFrom,5,2)
        transactionsArea.addWidget(self.labelTo,5,3)
        transactionsArea.addWidget(self.textTo,5,4)

        platformArea=QGridLayout(self)
        self.labelPlatform=QLabel()
        self.labelPlatform.setText("Select the platform:")
        self.labelPlatform.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboPlatforms = QComboBox(self)
        self.comboPlatforms.addItems(possiblePlatforms)
        self.comboPlatforms.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelOtherPlatform=QLabel()
        self.labelOtherPlatform.setText("If other, please specify")
        self.labelPlatform.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textOtherPlatform = QLineEdit()
        self.textOtherPlatform.setReadOnly(True)
        self.textOtherPlatform.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboPlatforms.currentIndexChanged.connect(self.comboPlatformsChange)
        platformArea.addWidget(self.labelPlatform,1,1)
        platformArea.addWidget(self.labelOtherPlatform,1,2)
        platformArea.addWidget(self.comboPlatforms,2,1)
        platformArea.addWidget(self.textOtherPlatform,2,2)

        currencyArea=QGridLayout(self)
        self.labelCurrency=QLabel()
        self.labelCurrency.setText("Select the currency:")
        self.labelCurrency.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboCurrencies = QComboBox(self)
        self.comboCurrencies.addItems(possibleCurrencies)
        self.comboCurrencies.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelOtherCurrency=QLabel()
        self.labelOtherCurrency.setText("If other, please specify")
        self.labelCurrency.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textOtherCurrency = QLineEdit()
        self.textOtherCurrency.setReadOnly(True)
        self.textOtherCurrency.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboCurrencies.currentIndexChanged.connect(self.comboCurrenciesChange)
        currencyArea.addWidget(self.labelCurrency,1,1)
        currencyArea.addWidget(self.labelOtherCurrency,1,2)
        currencyArea.addWidget(self.comboCurrencies,2,1)
        currencyArea.addWidget(self.textOtherCurrency,2,2)        

        shotArea=QGridLayout(self)
        self.labelShot=QLabel()
        self.labelShot.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelShot.setText("Select the type of screnshot:")
        self.comboShots = QComboBox(self)
        self.comboShots.addItems(possibleShots)
        self.comboShots.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.labelOtherShot=QLabel()
        self.labelOtherShot.setText("If other, please specify")
        self.labelOtherShot.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.textOtherShot = QLineEdit()
        self.textOtherShot.setReadOnly(True)
        self.textOtherShot.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.comboShots.currentIndexChanged.connect(self.comboShotsChange)
        shotArea.addWidget(self.labelShot,1,1)
        shotArea.addWidget(self.labelOtherShot,1,2)
        shotArea.addWidget(self.comboShots,2,1)
        shotArea.addWidget(self.textOtherShot,2,2)
        
        imageArea.addWidget(self.lbl,0, Qt.AlignCenter)

        dataArea.addWidget(self.labelCounter)
        dataArea.addWidget(self.labelName,1, Qt.AlignTop)

        dataArea.addLayout(languageArea,Qt.AlignLeft)
        # dataArea.addWidget(self.labelLanguage,0, Qt.AlignTop)
        # dataArea.addWidget(self.comboLanguage,0, Qt.AlignTop)
        # dataArea.addWidget(self.labelOtherLanguage,0, Qt.AlignTop)
        # dataArea.addWidget(self.textOtherLanguage,0, Qt.AlignTop)

        dataArea.addWidget(self.checkNoProof,0, Qt.AlignTop)
        dataArea.addLayout(noProofArea,Qt.AlignLeft)
        # dataArea.addWidget(self.labelNoProof,0, Qt.AlignTop)
        # dataArea.addWidget(self.comboNoProof,0, Qt.AlignTop)
        # dataArea.addWidget(self.labelOtherClass,0, Qt.AlignTop)
        # dataArea.addWidget(self.textOtherClass,1, Qt.AlignTop)
        dataArea.addWidget(self.labelAmount,0, Qt.AlignTop)
        dataArea.addWidget(self.textAmount,0, Qt.AlignTop)

        dataArea.addLayout(transactionsArea,Qt.AlignLeft)

        dataArea.addLayout(platformArea,Qt.AlignLeft)
        dataArea.addLayout(currencyArea,Qt.AlignLeft)
        # dataArea.addWidget(self.labelPlatform,0, Qt.AlignTop)
        # dataArea.addWidget(self.comboPlatforms,0, Qt.AlignTop)
        # dataArea.addWidget(self.labelOtherPlatform,0, Qt.AlignTop)
        # dataArea.addWidget(self.textOtherPlatform,0, Qt.AlignTop)

        dataArea.addLayout(shotArea,Qt.AlignLeft)
        # dataArea.addWidget(self.labelShot)
        # dataArea.addWidget(self.comboShots)
        # dataArea.addWidget(self.labelOtherShot)
        # dataArea.addWidget(self.textOtherShot)

        dataArea.addWidget(self.labelNotes,0,Qt.AlignTop)
        dataArea.addWidget(self.notes,1, Qt.AlignTop)

        dataArea.addLayout(buttonsArea)
        # dataArea.addWidget(self.previousButton)
        # dataArea.addWidget(self.nextButton)



        main.addLayout(imageArea,1,1)
        main.addLayout(dataArea,1,2)
        
        self.setLayout(main)
        self.move(300, 200)
        self.setWindowTitle('Image viewer')
        self.fillForms()
        self.showMaximized()
        #self.show()

    def transactionsChecked(self):
        global currentFile
        if self.checkTransactions.isChecked():
            self.labelNumTransactions.setStyleSheet("QLabel {color : black; }");
            self.labelTransactionAmount.setStyleSheet("QLabel {color : black; }");
            self.labelTransactionSpan.setStyleSheet("QLabel {color : black; }");
            self.labelTo.setStyleSheet("QLabel {color : black; }");
            self.labelFrom.setStyleSheet("QLabel {color : black; }");
            self.numTransactions.setReadOnly(False)
            self.textTransactionAmount.setReadOnly(False)
        else:
            self.labelNumTransactions.setStyleSheet("QLabel {color : gray; }");
            self.labelTransactionAmount.setStyleSheet("QLabel {color : gray; }");
            self.labelTransactionSpan.setStyleSheet("QLabel {color : gray; }");
            self.labelTo.setStyleSheet("QLabel {color : gray; }");
            self.labelFrom.setStyleSheet("QLabel {color : gray; }");            
            self.numTransactions.setReadOnly(True)
            self.textTransactionAmount.setReadOnly(True)

    def noProofChecked(self):
        global currentFile
        if self.checkNoProof.isChecked():
            self.labelNoProof.setStyleSheet("QLabel {color : black; }");
            self.labelOtherClass.setStyleSheet("QLabel {color : black; }");
            self.comboNoProof.setEnabled(True)
            #self.comboNoProofChange()

            self.labelPlatform.setStyleSheet("QLabel {color : gray; }");
            self.labelShot.setStyleSheet("QLabel {color : gray; }");
            self.labelOtherPlatform.setStyleSheet("QLabel {color : gray; }");
            self.labelOtherShot.setStyleSheet("QLabel {color : gray; }");
            self.labelCurrency.setStyleSheet("QLabel {color : gray; }");
            self.labelOtherCurrency.setStyleSheet("QLabel {color : gray; }");
            self.labelAmount.setStyleSheet("QLabel {color : gray; }");
            self.comboPlatforms.setEnabled(False)
            self.comboShots.setEnabled(False)
            self.comboCurrencies.setEnabled(False)
            self.textAmount.setReadOnly(True)
            self.textOtherPlatform.setReadOnly(True)
            self.textOtherShot.setReadOnly(True)
            self.textOtherCurrency.setReadOnly(True)
        
            self.checkTransactions.setEnabled(False)
            self.labelNumTransactions.setStyleSheet("QLabel {color : gray; }");
            self.labelTransactionAmount.setStyleSheet("QLabel {color : gray; }");
            self.labelTransactionSpan.setStyleSheet("QLabel {color : gray; }");
            self.labelTo.setStyleSheet("QLabel {color : gray; }");
            self.labelFrom.setStyleSheet("QLabel {color : gray; }");            
            self.numTransactions.setReadOnly(True)
            self.textTransactionAmount.setReadOnly(True)

        else:
            self.labelNoProof.setStyleSheet("QLabel {color : gray; }");
            self.labelOtherClass.setStyleSheet("QLabel {color : gray; }");
            self.comboNoProof.setEnabled(False)
            self.textOtherClass.setReadOnly(True)
            self.labelPlatform.setStyleSheet("QLabel {color : black; }");
            self.labelShot.setStyleSheet("QLabel {color : black; }");
            self.labelOtherPlatform.setStyleSheet("QLabel {color : black; }");
            self.labelOtherShot.setStyleSheet("QLabel {color : black; }");
            self.labelCurrency.setStyleSheet("QLabel {color : black; }");
            self.labelOtherCurrency.setStyleSheet("QLabel {color : black; }");
            self.labelAmount.setStyleSheet("QLabel {color : black; }");
            self.comboPlatforms.setEnabled(True)
            self.comboShots.setEnabled(True)
            self.comboCurrencies.setEnabled(True)
            self.textAmount.setReadOnly(False)
            self.textOtherPlatform.setReadOnly(False)
            self.textOtherShot.setReadOnly(False)
            self.textOtherCurrency.setReadOnly(False)
            self.checkTransactions.setEnabled(True)
            self.transactionsChecked()

            self.comboPlatformsChange()
            self.comboShotsChange()

    def comboLanguageChange(self):
        if self.comboLanguage.currentText()=='Other':
            self.textOtherLanguage.setReadOnly(False)
        else:
            self.textOtherLanguage.setReadOnly(True)
    def comboNoProofChange(self):
        if self.comboNoProof.currentText()=='Other':
            self.textOtherClass.setReadOnly(False)
        else:
            self.textOtherClass.setReadOnly(True)
    def comboPlatformsChange(self):
        if self.comboPlatforms.currentText()=='Other':
            self.textOtherPlatform.setReadOnly(False)
        else:
            self.textOtherPlatform.setReadOnly(True)
    def comboCurrenciesChange(self):
        if self.comboCurrencies.currentText()=='Other':
            self.textOtherCurrency.setReadOnly(False)
        else:
            self.textOtherCurrency.setReadOnly(True)
    def comboShotsChange(self):
        global currentFile
        if self.comboShots.currentText()=='Other':
            self.textOtherShot.setReadOnly(False)
        else:
            self.textOtherShot.setReadOnly(True)
    def nextImage(self):
        global currentFile
        self.saveCurrent()
        currentFile+=1
        if currentFile==len(fileNames):
            currentFile=0
        
        self.fillForms()
        
    def previousImage(self):
        global currentFile
        self.saveCurrent()
        currentFile-=1
        if currentFile==-1:
            currentFile=len(fileNames)-1
        self.fillForms()

    # Fill the GUI with the information from the current image
    def fillForms(self):
        global currentFile
        filename=fileNames[currentFile]

        if data[filename]['language'] in possibleLanguages:
            index=possibleLanguages.index(data[filename]['language'])
            self.comboLanguage.setCurrentIndex(index)
            self.textOtherLanguage.setText("")
        else:
            self.comboLanguage.setCurrentIndex(possibleLanguages.index('Other'))
            self.textOtherLanguage.setText(data[filename]['language'])

        self.notes.setText(data[filename]['notes'])

        self.checkNoProof.setChecked(not data[filename]['isProof'])
        if data[filename]['isProof']:
            if data[filename]['platform'] in possiblePlatforms:
                index=possiblePlatforms.index(data[filename]['platform'])
                self.comboPlatforms.setCurrentIndex(index)
                self.textOtherPlatform.setText("")
            else:
                self.comboPlatforms.setCurrentIndex(possiblePlatforms.index('Other'))
                self.textOtherPlatform.setText(data[filename]['platform'])

            if data[filename]['typeOfScreenshot'] in possibleShots:
                index=possibleShots.index(data[filename]['typeOfScreenshot'])
                self.comboShots.setCurrentIndex(index)
                self.textOtherShot.setText("")
            else:
                self.comboShots.setCurrentIndex(possibleShots.index('Other'))
                self.textOtherShot.setText(data[filename]['typeOfScreenshot'])

            if data[filename]['currency'] in possibleCurrencies:
                index=possibleCurrencies.index(data[filename]['currency'])
                self.comboCurrencies.setCurrentIndex(index)
                self.textOtherCurrency.setText("")
            else:
                self.comboCurrencies.setCurrentIndex(possibleCurrencies.index('Other'))
                self.textOtherCurrency.setText(data[filename]['currency'])   

            if data[filename]['totalAmount']>=0:
                self.textAmount.setText(str(data[filename]['totalAmount']))
            else:             
                self.textAmount.setText('')
            self.checkTransactions.setChecked(data[filename]['hasTransactions'])
            if data[filename]['hasTransactions']:
                if data[filename]['numTransactions']>0:
                    self.numTransactions.setText(str(data[filename]['numTransactions']))
                else:
                    self.numTransactions.setText('')
                if data[filename]['transactionTotal']>=0:
                    self.textTransactionAmount.setText(str(data[filename]['transactionTotal']))
                else:             
                    self.textTransactionAmount.setText('')                
                if data[filename]['transactionFrom']>=datetime.strptime('2000','%Y'):
                    self.textFrom.setText(data[filename]['transactionFrom'].strftime('%d/%m/%y'))
                else:             
                    self.textFrom.setText('')
                if data[filename]['transactionTo']>=datetime.strptime('2000','%Y'):
                    self.textTo.setText(data[filename]['transactionTo'].strftime('%d/%m/%y'))
                else:             
                    self.textTo.setText('')
            else:
                self.numTransactions.setText('')
                self.textTransactionAmount.setText('')
                self.textFrom.setText('')
                self.textTo.setText('')

            self.textOtherClass.setText("")
            self.comboNoProof.setCurrentIndex(0)
        else:
            if data[filename]['noProofClass'] in possibleClassesNoProof:
                index=possibleClassesNoProof.index(data[filename]['noProofClass'])
                self.comboNoProof.setCurrentIndex(index)
                self.textOtherClass.setText("")
            else:
                self.comboNoProof.setCurrentIndex(possibleClassesNoProof.index('Other'))
                self.textOtherClass.setText(data[filename]['noProofClass']) 
            self.comboCurrencies.setCurrentIndex(0)
            self.comboShots.setCurrentIndex(0)
            self.comboPlatforms.setCurrentIndex(0)
            self.textAmount.setText('')
            self.numTransactions.setText('')
            self.textTransactionAmount.setText('')
            self.textFrom.setText('')
            self.textTo.setText('') 
            self.textOtherCurrency.setText("") 
            self.textOtherShot.setText("")
            self.textOtherPlatform.setText("")     
        
        self.lbl.setScaledContents(True);
        self.lbl.setPixmap(QPixmap(filePaths[currentFile]))
        self.labelCounter.setText("Image %s of %s"%(currentFile+1,len(filePaths)))
        self.labelName.setText("Year %s"%fileNames[currentFile][:4])

    # Save the current image based on the GUI
    def saveCurrent(self):
        global currentFile,data
        filename=fileNames[currentFile]
        if not filename in data.keys():
            data[filename]={}
        data[filename]['notes']=self.notes.toPlainText()
        
        data[filename]['language']=self.comboLanguage.currentText()
        if data[filename]['language']=='Other':
            data[filename]['language']=self.textOtherLanguage.text()

        data[filename]['isProof']=not self.checkNoProof.isChecked()

        if data[filename]['isProof']:
            data[filename]['platform']=self.comboPlatforms.currentText()
            if data[filename]['platform']=='Other':
                data[filename]['platform']=self.textOtherPlatform.text()

            data[filename]['typeOfScreenshot']=self.comboShots.currentText()
            if data[filename]['typeOfScreenshot']=='Other':
                data[filename]['typeOfScreenshot']=self.textOtherShot.text()
            data[filename]['typeOfScreenshot']=self.comboShots.currentText()
            if data[filename]['typeOfScreenshot']=='Other':
                data[filename]['typeOfScreenshot']=self.textOtherShot.text()
            data[filename]['currency']=self.comboCurrencies.currentText()
            if data[filename]['currency']=='Other':
                data[filename]['currency']=self.textOtherCurrency.text()
            try:
                data[filename]['totalAmount']=float(self.textAmount.text())
            except:
                print ("Warning. File %s does not provide total"%filename)
                data[filename]['totalAmount']=-1
            data[filename]['hasTransactions']=self.checkTransactions.isChecked()
            if data[filename]['hasTransactions']:
                try:
                    data[filename]['numTransactions']=int(self.numTransactions.text())
                except:
                    print ("Warning. File %s does not provide numTransactions"%filename)
                    data[filename]['numTransactions']=-1                
                try:
                    data[filename]['transactionTotal']=float(self.textTransactionAmount.text())
                except:
                    print ("Warning. File %s does not provide transaction total"%filename)
                    data[filename]['transactionTotal']=-1
                try:
                    data[filename]['transactionFrom']=datetime.strptime(self.textFrom.text(),'%d/%m/%y')
                except:
                    print ("Warning. File %s does not provide transaction FROM"%filename)
                    data[filename]['transactionFrom']=datetime.strptime('01/01/99','%d/%m/%y')
                try: 
                    data[filename]['transactionTo']=datetime.strptime(self.textTo.text(),'%d/%m/%y')
                except:
                    print ("Warning. File %s does not provide transaction TO"%filename)
                    data[filename]['transactionTo']=datetime.strptime('01/01/99','%d/%m/%y')
            else:
                data[filename]['transactionTotal']=-1
                data[filename]['transactionFrom']=datetime.strptime('01/01/99','%d/%m/%y')
                data[filename]['transactionTo']=datetime.strptime('01/01/99','%d/%m/%y')
            
            data[filename]['noProofClass']='-'
        else:
            data[filename]['noProofClass']=self.comboNoProof.currentText()
            if data[filename]['noProofClass']=='Other':
                data[filename]['noProofClass']=self.textOtherClass.text()
            data[filename]['typeOfScreenshot']="-"
            data[filename]['platform']="-"
            data[filename]['currency']="-"
            data[filename]['hasTransactions']=False
            data[filename]['numTransactions']=0
            data[filename]['transactionTotal']=-1
            data[filename]['transactionFrom']=datetime.strptime('01/01/99','%d/%m/%y')
            data[filename]['transactionTo']=datetime.strptime('01/01/99','%d/%m/%y') 
            data[filename]['totalAmount']=-1

                   
    def closeEvent(self, event):
        global data
        print ("Saving data...")
        self.saveCurrent()

        pickle.dump((data,currentFile),open(DATA_FILE,'wb'))
        can_exit=True
        if can_exit:
            event.accept() # let the window close
        else:
            event.ignore()
def loadData():
    global data
    global currentFile

    if os.path.exists(DATA_FILE):
        data,currentFile=pickle.load(open(DATA_FILE,'rb'))
    else:
        data={}
        for filename in fileNames:
            data[filename]={}
            data[filename]['notes']=""
            data[filename]['totalAmount']=-1
            data[filename]['hasTransactions']=False
            data[filename]['numTransactions']=0
            data[filename]['transactionTotal']=-1
            data[filename]['transactionFrom']=datetime.strptime('01/01/99','%d/%m/%y')
            data[filename]['transactionTo']=datetime.strptime('01/01/99','%d/%m/%y')        
            data[filename]['isProof']=True
            data[filename]['currency']='Missing'
            data[filename]['platform']='Missing'
            data[filename]['typeOfScreenshot']='Missing'
            data[filename]['language']='English'
            data[filename]['noProofClass']='-'


if __name__ == '__main__':
    if len(sys.argv)!=3:
        print ("USAGE: python imageTagger.py <image-directory> <data-file>")
        exit(0)
    directory=sys.argv[1]
    DATA_FILE=sys.argv[2]
    filePaths=[directory + f for f in os.listdir(directory) if not f[0]=='.']
    fileNames=[f for f in os.listdir(directory) if not f[0]=='.']    
    loadData()
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())