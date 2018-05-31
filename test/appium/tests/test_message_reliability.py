import random
import string
import time

from itertools import cycle
from timeit import timeit
from selenium.common.exceptions import TimeoutException

from tests import info, marks
from tests.base_test_case import MessageReliabilityTestCase
from views.sign_in_view import SignInView


def wrapper(func, *args, **kwargs):
    def wrapped():
        return func(*args, **kwargs)

    return wrapped


@marks.message_reliability
class TestMessageReliability(MessageReliabilityTestCase):

    def test_message_reliability_1_1_chat(self, messages_number, message_wait_time):
        user_a_sent_messages = 0
        user_a_received_messages = 0
        user_b_sent_messages = 0
        user_b_received_messages = 0
        user_a_message_time = dict()
        user_b_message_time = dict()
        try:
            self.create_drivers(2, max_duration=10800, custom_implicitly_wait=2)
            device_1, device_2 = SignInView(self.drivers[0]), SignInView(self.drivers[1])
            device_1.create_user(username='user_a')
            device_2.create_user(username='user_b')
            device_1_home, device_2_home = device_1.get_home_view(), device_2.get_home_view()
            device_2_public_key = device_2_home.get_public_key()
            device_2_home.home_button.click()
            device_1_home.add_contact(device_2_public_key)
            device_1_chat = device_1_home.get_chat_view()
            device_1_chat.chat_message_input.send_keys('hello')
            device_1_chat.send_message_button.click()
            device_2_home.element_by_text('hello').click()
            device_2_chat = device_2_home.get_chat_view()
            device_2_chat.add_to_contacts.click()

            start_time = time.time()
            for i in range(int(messages_number / 2)):
                message_1 = ''.join(random.sample(string.ascii_lowercase, k=10))
                device_1_chat.chat_message_input.send_keys(message_1)
                device_1_chat.send_message_button.click()
                user_a_sent_messages += 1
                try:
                    user_b_receive_time = timeit(wrapper(device_2_chat.wait_for_element_starts_with_text,
                                                         message_1, message_wait_time),
                                                 number=1)
                    duration_time = round(time.time() - start_time, ndigits=2)
                    user_b_message_time[duration_time] = user_b_receive_time
                    user_b_received_messages += 1
                except TimeoutException:
                    info("Message with text '%s' was not received by user_b" % message_1)
                message_2 = ''.join(random.sample(string.ascii_lowercase, k=10))
                device_2_chat.chat_message_input.send_keys(message_2)
                device_2_chat.send_message_button.click()
                user_b_sent_messages += 1
                try:
                    user_a_receive_time = timeit(wrapper(device_1_chat.wait_for_element_starts_with_text,
                                                         message_2, message_wait_time),
                                                 number=1)
                    duration_time = round(time.time() - start_time, ndigits=2)
                    user_a_message_time[duration_time] = user_a_receive_time
                    user_a_received_messages += 1
                except TimeoutException:
                    info("Message with text '%s' was not received by user_a" % message_2)
        finally:
            self.one_to_one_chat_data['user_a'] = {'sent_messages': user_a_sent_messages,
                                                   'message_time': user_a_message_time}
            self.one_to_one_chat_data['user_b'] = {'sent_messages': user_b_sent_messages,
                                                   'message_time': user_b_message_time}

    def test_message_reliability_public_chat(self, messages_number, message_wait_time, participants_number):
        self.public_chat_data['sent_messages'] = int()
        self.public_chat_data['message_time'] = dict()

        self.create_drivers(participants_number, max_duration=10800, custom_implicitly_wait=2)
        users = list()
        chat_views = list()
        chat_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(7))
        for i in range(participants_number):
            device = SignInView(self.drivers[i])
            users.append(device.create_user())
            home_view = device.get_home_view()
            home_view.join_public_chat(chat_name)
            chat_views.append(home_view.get_chat_view())

        start_time = time.time()
        repeat = cycle(range(participants_number))
        for i in repeat:
            message_text = ''.join(random.sample(string.ascii_lowercase, k=10))
            chat_views[i].chat_message_input.send_keys(message_text)
            chat_views[i].send_message_button.click()
            self.public_chat_data['sent_messages'] += 1
            try:
                user_b_receive_time = timeit(wrapper(chat_views[next(repeat)].wait_for_element_starts_with_text,
                                                     message_text, message_wait_time),
                                             number=1)
                duration_time = round(time.time() - start_time, ndigits=2)
                self.public_chat_data['message_time'][duration_time] = user_b_receive_time
            except TimeoutException:
                pass
            if self.public_chat_data['sent_messages'] == messages_number:
                break

    def test_message_reliability_offline_public_chat(self, messages_number, message_wait_time):
        self.public_chat_data['sent_messages'] = int()
        self.public_chat_data['message_time'] = dict()

        self.create_drivers(1, max_duration=10800, custom_implicitly_wait=2, offline_mode=True)
        driver = self.drivers[0]
        sign_in_view = SignInView(driver)
        sign_in_view.create_user()
        home_view = sign_in_view.get_home_view()
        chat_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(7))
        home_view.join_public_chat(chat_name)

        start_time = time.time()
        iterations = int(messages_number / 10 if messages_number > 10 else messages_number)
        for _ in range(iterations):
            home_view.get_back_to_home_view()
            driver.set_network_connection(1)  # airplane mode

            sent_messages_texts = self.network_api.start_chat_bot(chat_name=chat_name, messages_number=10)
            self.public_chat_data['sent_messages'] += 10

            driver.set_network_connection(2)  # turning on WiFi connection

            home_view.get_chat_with_user('#' + chat_name).click()
            chat_view = home_view.get_chat_view()
            for message in sent_messages_texts:
                try:
                    user_b_receive_time = timeit(wrapper(chat_view.wait_for_element_starts_with_text,
                                                         message, message_wait_time),
                                                 number=1)
                    duration_time = round(time.time() - start_time, ndigits=2)
                    self.public_chat_data['message_time'][duration_time] = user_b_receive_time
                except TimeoutException:
                    pass
