# hashids Python port
# Written by Eric Martel - www.ericmartel.com
# Licensed under MIT - see LICENSE

import re

class hashids():
    version = '0.0.1'
    # why this alphabet is chosen?
    __alphabet = 'xcS4F6h89aUbideAI7tkynuopqrXCgTE5GBKHLMjfRsz'
    # why these indexes are chosen?
    __primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43]
    __minHashLength = 0

    def __init__(self, salt = '', minHashLength = 0, alphabet = None):
        self.__salt = salt

        if not isinstance(self.__salt, str):
            raise ValueError('Salt should be a string')

        if(minHashLength != None and isinstance(minHashLength, int) and minHashLength > 0):
            self.__minHashLength = minHashLength

        if(alphabet != None and isinstance(alphabet, str) and len(alphabet) > 0):
            # Make sure the user created alphabet only contains unique values
            newAlphabet = [];
            seen = {}

            for symbol in list(alphabet):
                if symbol in seen: continue
                seen[symbol] = 1
                newAlphabet.append(symbol)

            self.__alphabet = ''.join(newAlphabet)

            if(len(self.__alphabet) < 4):
                raise ValueError('The alphabet should contain at least 4 unique symbols')

        self.__guards = [];
        self.__seps = [];

        # throw away those characters from the __alphabet which are on the positons of __primes
        # it results in having the original __alphabet containing 44-14=30 characters
        for prime in self.__primes:
            if prime - 1 > len(self.__alphabet):
                break

            character = self.__alphabet[prime - 1];
            self.__seps.append(character)
            self.__alphabet = self.__alphabet.replace(character, ' ')

        # throw away those characters from the __seps which are on specified positions
        # and put them into __guards resulting 5 characters in __gruards and 13-5=7 characters in __seps
        for index in [0, 4, 8, 12]:
            if index > len(self.__seps):
                break

            sep = self.__seps[index]
            self.__guards.append(sep)
            self.__seps.remove(sep)

        self.__alphabet = self.__alphabet.replace(' ', '')
        self.__alphabet = self.__consistentShuffle(self.__alphabet, self.__salt)

    def encrypt(self, *values):
        ret = ''

        if len(values) == 0:
            return ret

        for number in values:
            if not isinstance(number, int) or number < 0:
                return ret

        return self.__encode(values, self.__alphabet, self.__salt, self.__minHashLength)

    def decrypt(self, hash):

        ret = []

        if not hash or not isinstance(hash, str):
            raise ValueError('Hash should be a string')

        return self.__decode(hash)

    def __encode(self, values, alphabet, salt, minHashLength):
        ret = ''

        seps = list(self.__consistentShuffle(self.__seps, values))

        for idx, val in enumerate(values):
            if not idx:
                # for the first iteration create a lotterySalt consisting of v1-v2-...-vn-(v1+1)*2-(v2+1)*2-...-(vn+1)*2
                lotterySalt = '-'.join(map(lambda num: str(num), values))
                lotterySalt += '-'
                lotterySalt += '-'.join(map(lambda num: str((num+1)*2), values))

                lottery = self.__consistentShuffle(alphabet, lotterySalt)
                lotteryChar = lottery[0]
                ret += lotteryChar

                alphabet = lotteryChar + alphabet.replace(lotteryChar, '')

            alphabet = self.__consistentShuffle(alphabet, str((ord(lotteryChar) & 12345)) + salt)
            ret += self.__hash(val, alphabet)

            if idx + 1 < len(values):
                sepsIndex = (val + idx) % len(seps)
                ret += seps[sepsIndex]

        if len(ret) < minHashLength:
            firstIndex = 0
            for idx, val in enumerate(values):
                firstIndex += (idx + 1) * val

            guardIndex = firstIndex % len(self.__guards)
            guard = self.__guards[guardIndex]

            ret = guard + ret
            if len(ret) < minHashLength:
                guardIndex = (guardIndex + len(ret)) % len(self.__guards)
                guard = self.__guards[guardIndex]

                ret += guard

        while len(ret) < minHashLength:
            padArray = [ord(alphabet[1]), ord(alphabet[0])]

            padLeft = self.__encode(padArray, alphabet, salt)
            padRight = self.__encode(padArray, alphabet, ''.join(padArray))

            ret = padLeft + ret + padRight
            excess = len(ret) - minHashLength

            if excess > 0:
                trim = excess / 2
                ret = ret[trim:minHashLength + trim]

            alphabet = self.__consistentShuffle(alphabet, salt + ret)

        return ret

    def __decode(self, hash):
        ret = []

        if len(hash):
            originalHash = hash

            hash = re.sub('[%s]' % ''.join(self.__guards), '', hash)
            hashExplode = hash.split(' ')

            i = 0
            if len(hashExplode) == 3 or len(hashExplode) == 2:
                i = 1

            hash = hashExplode[i]

            hash = re.sub('[%s]' % ''.join(self.__seps), ' ', hash) 
            hashArray = hash.split(' ')

            alphabet = ""
            lotteryChar = ''

            for idx, subHash in enumerate(hashArray):
                if len(subHash):
                    if not idx:
                        lotteryChar = hash[0]
                        subHash = subHash[1:]
                        alphabet = lotteryChar + self.__alphabet.replace(lotteryChar, '')

                    alphabet = self.__consistentShuffle(alphabet, str(ord(lotteryChar) & 12345) + self.__salt)
                    number = self.__unhash(subHash, alphabet);
                    ret.append(number)

            encryptResult = self.encrypt(*ret)
            if encryptResult != originalHash:
                ret = [];
        return ret

    def __consistentShuffle(self, alphabet, salt):
        '''
        Shuffles the alphabet wrt the given salt.
        The resulting alphabet will consist of the same characters as the original one appearing on different places.
        "Consistent" implies that given the same alphabet and same salt result will be the same
        '''
        ret = ''

        if type(alphabet) is list:
            alphabet = ''.join(alphabet)

        if type(salt) is list:
            salt = ''.join(salt)
        if type(salt) is tuple:
            salt = ''.join('%d' % num for num in salt)

        if alphabet:
            alphabetArray = list(alphabet)
            saltArray = list(salt)

            shuffledIndexesArray = map(lambda char: ord(char), saltArray)

            # why exactly that whay of obtaining new indexes is chosen
            for i in range(len(shuffledIndexesArray)):
                add = True

                for k in range(i, len(shuffledIndexesArray) + i - 1):
                    nextIndex = (k + 1) % len(shuffledIndexesArray)

                    if add:
                        shuffledIndexesArray[i] += shuffledIndexesArray[nextIndex] + (k * i)
                    else:
                        shuffledIndexesArray[i] -= shuffledIndexesArray[nextIndex]

                    add = not add

                shuffledIndexesArray[i] = abs(shuffledIndexesArray[i])

            # construct the result by choosing an alphabet character at the shuffled index 
            i = 0
            shuffledIndexesArraySize = len(shuffledIndexesArray)
            while len(alphabetArray) > 0:

                pos = shuffledIndexesArray[i] % len(alphabetArray)

                ret += alphabetArray.pop(pos)

                i = (i + 1) % shuffledIndexesArraySize

        return ret if len(ret) > 0 else ''.join(alphabet)

    def __hash(self, input, alphabet):
        hash = ''
        alphabetLength = len(alphabet)

        while True:
            index = (input % alphabetLength)

            hash = alphabet[index] + hash
            input = int(input / alphabetLength)

            if not input:
                break;
        return hash

    def __unhash(self, input, alphabet):
        number = 0

        if len(input) and alphabet:
            alphabetLength = len(alphabet)
            inputChars = input[::1]

            for idx, character in enumerate(inputChars):
                pos = alphabet.find(character)
                number += pos * pow(alphabetLength, (len(input) - idx - 1))

        return number
