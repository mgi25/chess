export const rulesText = [
  "What is a Swiss-style Tournament?",
  "Right, so what are we trying to do anyway? We’re trying to code a Tournament Manager, which is useful for things like e-sports, trading card games, and anything else that’s vaguely competitive. In general, tournaments aim to determine the best player/team (I’ll just use player from now on) in a competition; obviously, the best way to go about this is to make each participant play each other, and the player with the highest score at the end of it all wins — this is known as a “Round-Robin” style tournament.",
  "The problem with a Round-Robin tournament is that it doesn’t scale very well to large numbers of participants. For example, 4-player round-robin tournament requires 3 rounds to be played. But the same tournament style for 32 players would require 31 rounds — a logistical nightmare at beast.",
  "Swiss-style tournaments were developed to counteract this problem. Swiss-style tournaments generally have two rules:",
  "Participants are paired with opponents who have similar scores.",
  "Participants cannot play the same opponent twice.",
  "In this way, the tournament aims to pair similarly ranked players until a winner is determined, and this process generally takes much fewer rounds than a round-robin tournament to resolve. For example, a 32-player Swiss tournament would only need 5 rounds to conclude rather than a 31-Round-Robin tournament — much better!",
  "Thus, to create our Tournament Manager app, we’re first going to need to come with an algorithm that does the above."
];

export const players = [
  {
    "id": 1,
    "name": "aditya dhyani",
    "fullName": "Aditya Dhyani",
    "contact": "9557648750",
    "department": "bcs csds",
    "registerNumber": "25112001",
    "seed": 94
  },
  {
    "id": 2,
    "name": "Ananth Krishna NB",
    "fullName": "Ananth Krishna Nb",
    "contact": "9448780711",
    "department": "1 BBA LLB",
    "registerNumber": "",
    "seed": 33
  },
  {
    "id": 3,
    "name": "saurya thakkar",
    "fullName": "Saurya Thakkar",
    "contact": "9724297440",
    "department": "1 BscCSDS PLC",
    "registerNumber": "",
    "seed": 10
  },
  {
    "id": 4,
    "name": "Thakkar harmik",
    "fullName": "Thakkar Harmik",
    "contact": "8200226290",
    "department": "1MSCDS",
    "registerNumber": "",
    "seed": 76
  },
  {
    "id": 5,
    "name": "Santhoshkrishna GM",
    "fullName": "Santhoshkrishna Gm",
    "contact": "9585851325",
    "department": "5BBA.LLB",
    "registerNumber": "23113158",
    "seed": 50
  },
  {
    "id": 6,
    "name": "kaif khan",
    "fullName": "Kaif Khan",
    "contact": "8542066736",
    "department": "1BBA BA",
    "registerNumber": "",
    "seed": 29
  },
  {
    "id": 7,
    "name": "HIMANSHU RAJ",
    "fullName": "Himanshu Raj",
    "contact": "9509444178",
    "department": "BBA BA",
    "registerNumber": "25111216",
    "seed": 63
  },
  {
    "id": 8,
    "name": "Swastik Pandey",
    "fullName": "Swastik Pandey",
    "contact": "9369555028",
    "department": "1 BSC ES",
    "registerNumber": "",
    "seed": 97
  },
  {
    "id": 9,
    "name": "Alen Join Shibu",
    "fullName": "Alen Join Shibu",
    "contact": "8590542504",
    "department": "5BSc.DS",
    "registerNumber": "",
    "seed": 70
  },
  {
    "id": 10,
    "name": "Aviroop Sinha",
    "fullName": "Aviroop Sinha",
    "contact": "9330829658",
    "department": "3BCom Fa",
    "registerNumber": "",
    "seed": 52
  },
  {
    "id": 11,
    "name": "Anjali Shitole",
    "fullName": "Anjali Shitole",
    "contact": "8369694689",
    "department": "1st year BCA",
    "registerNumber": "",
    "seed": 34
  },
  {
    "id": 12,
    "name": "Lingeswer.S",
    "fullName": "Lingeswer.S",
    "contact": "8072293969",
    "department": "1Bba Llb",
    "registerNumber": "",
    "seed": 90
  },
  {
    "id": 13,
    "name": "Ansh Kalra",
    "fullName": "Ansh Kalra",
    "contact": "6375855016",
    "department": "3 BBA BA A",
    "registerNumber": "24111105",
    "seed": 88
  },
  {
    "id": 14,
    "name": "Dhepeshnarayana.s",
    "fullName": "Dhepeshnarayana.S",
    "contact": "7358787286",
    "department": "1ba llb",
    "registerNumber": "",
    "seed": 11
  },
  {
    "id": 15,
    "name": "Harshvardhan Singh Rathore",
    "fullName": "Harshvardhan Singh Rathore",
    "contact": "7426885333",
    "department": "MBA",
    "registerNumber": "",
    "seed": 80
  },
  {
    "id": 16,
    "name": "Hans M Abraham",
    "fullName": "Hans M Abraham",
    "contact": "7902354121",
    "department": "1MBA",
    "registerNumber": "25121017",
    "seed": 41
  },
  {
    "id": 17,
    "name": "Akshay K S",
    "fullName": "Akshay K S",
    "contact": "8269780209",
    "department": "3ba llb",
    "registerNumber": "",
    "seed": 86
  },
  {
    "id": 18,
    "name": "Rishit Mishra",
    "fullName": "Rishit Mishra",
    "contact": "6307878572",
    "department": "1BBA BA C",
    "registerNumber": "",
    "seed": 87
  },
  {
    "id": 19,
    "name": "Akshat Chauhan",
    "fullName": "Akshat Chauhan",
    "contact": "8004100091",
    "department": "1 BA LLB PLC",
    "registerNumber": "25113007",
    "seed": 24
  },
  {
    "id": 20,
    "name": "Varghese Anto",
    "fullName": "Varghese Anto",
    "contact": "8907086495",
    "department": "9BBA LLB",
    "registerNumber": "21113185",
    "seed": 20
  },
  {
    "id": 21,
    "name": "Jatin",
    "fullName": "Jatin",
    "contact": "8005542110",
    "department": "5Bba b",
    "registerNumber": "23111432",
    "seed": 67
  },
  {
    "id": 22,
    "name": "Aryan Mhaskar",
    "fullName": "Aryan Mhaskar",
    "contact": "9335496172",
    "department": "7BALLB",
    "registerNumber": "22113013",
    "seed": 51
  },
  {
    "id": 23,
    "name": "Utsav Sahare",
    "fullName": "Utsav Sahare",
    "contact": "7558261659",
    "department": "BBA BA",
    "registerNumber": "",
    "seed": 58
  },
  {
    "id": 24,
    "name": "Kunal",
    "fullName": "Kunal",
    "contact": "9560275329",
    "department": "5 BBA D",
    "registerNumber": "",
    "seed": 4
  },
  {
    "id": 25,
    "name": "Tuba Ahmed",
    "fullName": "Tuba Ahmed",
    "contact": "9625974785",
    "department": "1bse es",
    "registerNumber": "",
    "seed": 85
  },
  {
    "id": 26,
    "name": "Adrika gosh",
    "fullName": "Adrika Gosh",
    "contact": "7003446716",
    "department": "1MSCDS",
    "registerNumber": "",
    "seed": 6
  },
  {
    "id": 27,
    "name": "Aditi Sai",
    "fullName": "Aditi Sai",
    "contact": "8109228681",
    "department": "Bcom",
    "registerNumber": "",
    "seed": 58
  },
  {
    "id": 28,
    "name": "Jai Sinnh Bhargava",
    "fullName": "Jai Sinnh Bhargava",
    "contact": "9971449460",
    "department": "1 Bcom A",
    "registerNumber": "",
    "seed": 44
  },
  {
    "id": 29,
    "name": "Priyanshu Mehra",
    "fullName": "Priyanshu Mehra",
    "contact": "9560930597",
    "department": "1 bba ba",
    "registerNumber": "25113154",
    "seed": 55
  },
  {
    "id": 30,
    "name": "Sparsh Ahuja",
    "fullName": "Sparsh Ahuja",
    "contact": "9958472477",
    "department": "9 Ba Llb",
    "registerNumber": "21113078",
    "seed": 78
  },
  {
    "id": 31,
    "name": "Sherick Matthew",
    "fullName": "Sherick Matthew",
    "contact": "8098309889",
    "department": "9BBAllb",
    "registerNumber": "",
    "seed": 4
  },
  {
    "id": 32,
    "name": "Karasala Abishai",
    "fullName": "Karasala Abishai",
    "contact": "9989959685",
    "department": "5BBA C",
    "registerNumber": "23111523",
    "seed": 86
  },
  {
    "id": 33,
    "name": "Devkrishna",
    "fullName": "Devkrishna",
    "contact": "8590286754",
    "department": "5BSCDS",
    "registerNumber": "",
    "seed": 45
  },
  {
    "id": 34,
    "name": "Sahil kadu",
    "fullName": "Sahil Kadu",
    "contact": "7737824141",
    "department": "3BCA",
    "registerNumber": "",
    "seed": 27
  },
  {
    "id": 35,
    "name": "Divyansh",
    "fullName": "Divyansh",
    "contact": "9319828001",
    "department": "1 BSC ES",
    "registerNumber": "",
    "seed": 40
  },
  {
    "id": 36,
    "name": "Siddharth",
    "fullName": "Siddharth",
    "contact": "9789486803",
    "department": "9BBALLB",
    "registerNumber": "21113177",
    "seed": 55
  },
  {
    "id": 37,
    "name": "prince",
    "fullName": "Prince",
    "contact": "7039314403",
    "department": "3Ballb",
    "registerNumber": "",
    "seed": 32
  },
  {
    "id": 38,
    "name": "Arunabha Dey",
    "fullName": "Arunabha Dey",
    "contact": "8336089666",
    "department": "",
    "registerNumber": "",
    "seed": 68
  },
  {
    "id": 39,
    "name": "Anwesh Chatterjee",
    "fullName": "Anwesh Chatterjee",
    "contact": "6289121218",
    "department": "3BBA A",
    "registerNumber": "",
    "seed": 12
  },
  {
    "id": 40,
    "name": "Devagya Singla",
    "fullName": "Devagya Singla",
    "contact": "6283999788",
    "department": "1 BBA BA",
    "registerNumber": "",
    "seed": 94
  },
  {
    "id": 41,
    "name": "Abhinay Sahu",
    "fullName": "Abhinay Sahu",
    "contact": "7722867533",
    "department": "",
    "registerNumber": "",
    "seed": 82
  },
  {
    "id": 42,
    "name": "Rushiraj Patel",
    "fullName": "Rushiraj Patel",
    "contact": "9773265329",
    "department": "1BBA HONS",
    "registerNumber": "25111533",
    "seed": 84
  },
  {
    "id": 43,
    "name": "Jovian Anderson Chyne",
    "fullName": "Jovian Anderson Chyne",
    "contact": "9226464409",
    "department": "BSC. ES",
    "registerNumber": "25112306",
    "seed": 26
  },
  {
    "id": 44,
    "name": "arshad PR",
    "fullName": "Arshad Pr",
    "contact": "9526066338",
    "department": "9BA LLB",
    "registerNumber": "21113011",
    "seed": 61
  },
  {
    "id": 45,
    "name": "Buddha Hari Haran",
    "fullName": "Buddha Hari Haran",
    "contact": "9390220625",
    "department": "5BBA B",
    "registerNumber": "23111423",
    "seed": 41
  },
  {
    "id": 46,
    "name": "Vishal Yadav",
    "fullName": "Vishal Yadav",
    "contact": "9588501055",
    "department": "1BCA",
    "registerNumber": "",
    "seed": 14
  },
  {
    "id": 47,
    "name": "Yogyata Singh",
    "fullName": "Yogyata Singh",
    "contact": "8789739266",
    "department": "1BSCCSDS",
    "registerNumber": "",
    "seed": 74
  },
  {
    "id": 48,
    "name": "Vashitav Bali",
    "fullName": "Vashitav Bali",
    "contact": "9541355388",
    "department": "1bcom",
    "registerNumber": "25114045",
    "seed": 21
  },
  {
    "id": 49,
    "name": "Devesh Tiwari",
    "fullName": "Devesh Tiwari",
    "contact": "8400616871",
    "department": "5BBA",
    "registerNumber": "23113120",
    "seed": 37
  },
  {
    "id": 50,
    "name": "Harshith Shresth",
    "fullName": "Harshith Shresth",
    "contact": "",
    "department": "BBA BA",
    "registerNumber": "25111249",
    "seed": 55
  }
];

export const initialPairings = [
  {
    "table": 1,
    "player1": 43,
    "player2": 8,
    "player1Name": "Jovian Anderson Chyne",
    "player2Name": "Swastik Pandey"
  },
  {
    "table": 2,
    "player1": 37,
    "player2": 50,
    "player1Name": "Prince",
    "player2Name": "Harshith Shresth"
  },
  {
    "table": 3,
    "player1": 16,
    "player2": 10,
    "player1Name": "Hans M Abraham",
    "player2Name": "Aviroop Sinha"
  },
  {
    "table": 4,
    "player1": 9,
    "player2": 44,
    "player1Name": "Alen Join Shibu",
    "player2Name": "Arshad Pr"
  },
  {
    "table": 5,
    "player1": 6,
    "player2": 22,
    "player1Name": "Kaif Khan",
    "player2Name": "Aryan Mhaskar"
  },
  {
    "table": 6,
    "player1": 7,
    "player2": 4,
    "player1Name": "Himanshu Raj",
    "player2Name": "Thakkar Harmik"
  },
  {
    "table": 7,
    "player1": 36,
    "player2": 48,
    "player1Name": "Siddharth",
    "player2Name": "Vashitav Bali"
  },
  {
    "table": 8,
    "player1": 19,
    "player2": 20,
    "player1Name": "Akshat Chauhan",
    "player2Name": "Varghese Anto"
  },
  {
    "table": 9,
    "player1": 42,
    "player2": 17,
    "player1Name": "Rushiraj Patel",
    "player2Name": "Akshay K S"
  },
  {
    "table": 10,
    "player1": 3,
    "player2": 18,
    "player1Name": "Saurya Thakkar",
    "player2Name": "Rishit Mishra"
  },
  {
    "table": 11,
    "player1": 25,
    "player2": 28,
    "player1Name": "Tuba Ahmed",
    "player2Name": "Jai Sinnh Bhargava"
  },
  {
    "table": 12,
    "player1": 47,
    "player2": 33,
    "player1Name": "Yogyata Singh",
    "player2Name": "Devkrishna"
  },
  {
    "table": 13,
    "player1": 11,
    "player2": 45,
    "player1Name": "Anjali Shitole",
    "player2Name": "Buddha Hari Haran"
  },
  {
    "table": 14,
    "player1": 30,
    "player2": 40,
    "player1Name": "Sparsh Ahuja",
    "player2Name": "Devagya Singla"
  },
  {
    "table": 15,
    "player1": 21,
    "player2": 31,
    "player1Name": "Jatin",
    "player2Name": "Sherick Matthew"
  },
  {
    "table": 16,
    "player1": 2,
    "player2": 24,
    "player1Name": "Ananth Krishna Nb",
    "player2Name": "Kunal"
  },
  {
    "table": 17,
    "player1": 38,
    "player2": 23,
    "player1Name": "Arunabha Dey",
    "player2Name": "Utsav Sahare"
  },
  {
    "table": 18,
    "player1": 32,
    "player2": 41,
    "player1Name": "Karasala Abishai",
    "player2Name": "Abhinay Sahu"
  },
  {
    "table": 19,
    "player1": 46,
    "player2": 12,
    "player1Name": "Vishal Yadav",
    "player2Name": "Lingeswer.S"
  },
  {
    "table": 20,
    "player1": 39,
    "player2": 26,
    "player1Name": "Anwesh Chatterjee",
    "player2Name": "Adrika Gosh"
  },
  {
    "table": 21,
    "player1": 1,
    "player2": 29,
    "player1Name": "Aditya Dhyani",
    "player2Name": "Priyanshu Mehra"
  },
  {
    "table": 22,
    "player1": 49,
    "player2": 14,
    "player1Name": "Devesh Tiwari",
    "player2Name": "Dhepeshnarayana.S"
  },
  {
    "table": 23,
    "player1": 15,
    "player2": 35,
    "player1Name": "Harshvardhan Singh Rathore",
    "player2Name": "Divyansh"
  },
  {
    "table": 24,
    "player1": 5,
    "player2": 13,
    "player1Name": "Santhoshkrishna Gm",
    "player2Name": "Ansh Kalra"
  },
  {
    "table": 25,
    "player1": 34,
    "player2": 27,
    "player1Name": "Sahil Kadu",
    "player2Name": "Aditi Sai"
  }
];
