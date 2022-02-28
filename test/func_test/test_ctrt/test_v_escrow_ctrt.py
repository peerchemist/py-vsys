import asyncio
import time
from typing import Tuple

import pytest

import py_v_sdk as pv
from test.func_test import conftest as cft


class TestVEscrowCtrt:
    """
    TestVEscrowCtrt is the collection of functional tests of V Escrow Contract.
    """

    ORDER_AMOUNT = 10
    RCPT_DEPOSIT_AMOUNT = 2
    JUDGE_DEPOSIT_AMOUNT = 3
    ORDER_FEE = 4
    REFUND_AMOUNT = 5
    CTRT_DEPOSIT_AMOUNT = 30

    @pytest.fixture
    def maker(self, acnt0: pv.Account) -> pv.Account:
        """
        maker is the fixture that returns the maker account used in the tests.

        Args:
            acnt0 (pv.Account): The account of nonce 0.

        Returns:
            pv.Account: The account.
        """
        return acnt0

    @pytest.fixture
    def judge(self, acnt0: pv.Account) -> pv.Account:
        """
        judge is the fixture that returns the judge account used in the tests.

        Args:
            acnt0 (pv.Account): The account of nonce 0.

        Returns:
            pv.Account: The account.
        """
        return acnt0

    @pytest.fixture
    def payer(self, acnt1: pv.Account) -> pv.Account:
        """
        payer is the fixture that returns the payer account used in the tests.

        Args:
            acnt0 (pv.Account): The account of nonce 0.

        Returns:
            pv.Account: The account.
        """
        return acnt1

    @pytest.fixture
    def recipient(self, acnt2: pv.Account) -> pv.Account:
        """
        recipient is the fixture that returns the recipient account used in the tests.

        Args:
            acnt0 (pv.Account): The account of nonce 0.

        Returns:
            pv.Account: The account.
        """
        return acnt2

    @pytest.fixture
    async def new_sys_ctrt(self, chain: pv.Chain) -> pv.SysCtrt:
        """
        new_sys_ctrt is the fixture that returns a system contract instance.

        Args:
            chain (pv.Chain): The chain object.

        Returns:
            pv.SysCtrt: The system contract instance.
        """
        return pv.SysCtrt.for_testnet(chain)

    async def _new_ctrt(
        self,
        new_sys_ctrt: pv.SysCtrt,
        maker: pv.Account,
        judge: pv.Account,
        payer: pv.Account,
        recipient: pv.Account,
        duration: int,
    ) -> pv.VEscrowCtrt:
        """
        _new_ctrt registers a new V Escrow Contract where the payer duration & judge duration
        are all the given duration.

        Args:
            new_sys_ctrt (pv.SysCtrt): The system contract instance.
            maker (pv.Account): The account of the contract maker.
            judge (pv.Account): The account of the contract judge.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.
            duration (int): The duration in seconds.

        Returns:
            pv.VEscrowCtrt: The VEscrowCtrt instance.
        """
        sc = new_sys_ctrt
        api = maker.api

        vc = await pv.VEscrowCtrt.register(
            by=maker,
            tok_id=sc.tok_id,
            duration=duration,
            judge_duration=duration,
        )
        await cft.wait_for_block()

        judge_resp, payer_resp, rcpt_resp = await asyncio.gather(
            sc.deposit(judge, vc.ctrt_id, self.CTRT_DEPOSIT_AMOUNT),
            sc.deposit(payer, vc.ctrt_id, self.CTRT_DEPOSIT_AMOUNT),
            sc.deposit(recipient, vc.ctrt_id, self.CTRT_DEPOSIT_AMOUNT),
        )
        await cft.wait_for_block()

        await asyncio.gather(
            cft.assert_tx_success(api, judge_resp["id"]),
            cft.assert_tx_success(api, payer_resp["id"]),
            cft.assert_tx_success(api, rcpt_resp["id"]),
        )
        return vc

    @pytest.fixture
    async def new_ctrt_ten_mins(
        self,
        new_sys_ctrt: pv.SysCtrt,
        maker: pv.Account,
        judge: pv.Account,
        payer: pv.Account,
        recipient: pv.Account,
    ) -> pv.VEscrowCtrt:
        """
        new_ctrt_ten_mins is the fixture that registers
        a new V Escrow Contract where the payer duration & judge duration
        are all 10 mins

        Args:
            new_sys_ctrt (pv.SysCtrt): The system contract instance.
            maker (pv.Account): The account of the contract maker.
            judge (pv.Account): The account of the contract judge.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.

        Returns:
            pv.VEscrowCtrt: The VEscrowCtrt instance.
        """
        ten_mins = 10 * 60
        return await self._new_ctrt(
            new_sys_ctrt,
            maker,
            judge,
            payer,
            recipient,
            ten_mins,
        )

    @pytest.fixture
    async def new_ctrt_five_secs(
        self,
        new_sys_ctrt: pv.SysCtrt,
        maker: pv.Account,
        judge: pv.Account,
        payer: pv.Account,
        recipient: pv.Account,
    ) -> pv.VEscrowCtrt:
        """
        new_ctrt_ten_mins is the fixture that registers
        a new V Escrow Contract where the payer duration & judge duration
        are all 5 secs.

        Args:
            new_sys_ctrt (pv.SysCtrt): The system contract instance.
            maker (pv.Account): The account of the contract maker.
            judge (pv.Account): The account of the contract judge.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.

        Returns:
            pv.VEscrowCtrt: The VEscrowCtrt instance.
        """
        five_secs = 5
        return await self._new_ctrt(
            new_sys_ctrt,
            maker,
            judge,
            payer,
            recipient,
            five_secs,
        )

    async def _create_order(
        self,
        ctrt: pv.VEscrowCtrt,
        payer: pv.Account,
        recipient: pv.Account,
        expire_at: int = 0,
    ) -> Tuple[pv.VEscrowCtrt, str]:
        """
        _create_order creates an order for the given V Escrow contract.

        Args:
            ctrt (pv.VEscrowCtrt): A V Escrow contract instance.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.

        Returns:
            Tuple[pv.VEscrowCtrt, str]: The VEscrowCtrt instance and the order_id.
        """
        vc = ctrt
        api = payer.api

        if expire_at == 0:
            a_day_later = int(time.time()) + 60 * 60 * 24
            expire_at = a_day_later

        resp = await vc.create(
            by=payer,
            recipient=recipient.addr.b58_str,
            amount=self.ORDER_AMOUNT,
            rcpt_deposit_amount=self.RCPT_DEPOSIT_AMOUNT,
            judge_deposit_amount=self.JUDGE_DEPOSIT_AMOUNT,
            order_fee=self.ORDER_FEE,
            refund_amount=self.REFUND_AMOUNT,
            expire_at=expire_at,
        )
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])
        order_id = resp["id"]

        return vc, order_id

    @pytest.fixture
    async def new_ctrt_ten_mins_order(
        self,
        new_ctrt_ten_mins: pv.VEscrowCtrt,
        payer: pv.Account,
        recipient: pv.Account,
    ) -> Tuple[pv.VEscrowCtrt, str]:
        """
        new_ctrt_ten_mins_order is the fixture that registers
        a new V Escrow Contract where the payer duration & judge duration
        are all 10 mins with an order created.

        Args:
            new_ctrt_ten_mins (pv.VEscrowCtrt): The V Escrow contract instance.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.

        Returns:
            Tuple[pv.VEscrowCtrt, str]: The VEscrowCtrt instance and the order_id
        """
        vc = new_ctrt_ten_mins
        return await self._create_order(vc, payer, recipient)

    async def _deposit_to_order(
        self,
        ctrt: pv.VEscrowCtrt,
        order_id: str,
        recipient: pv.Account,
        judge: pv.Account,
    ) -> Tuple[pv.VEscrowCtrt, str]:
        """
        _deposit_to_order ensures every party has deposited into the order.

        Args:
            ctrt (pv.VEscrowCtrt): A V Escrow contract instance.
            order_id (str): The order ID.
            recipient (pv.Account): The account of the contract recipient.
            judge (pv.Account): The account of the contract judge.

        Returns:
            Tuple[pv.VEscrowCtrt, str]: The VEscrowCtrt instance and the order_id.
        """
        vc = ctrt
        api = recipient.api

        # payer has deposited when creating the order
        # Let recipient & judge deposit

        rcpt_resp, judge_resp = await asyncio.gather(
            vc.recipient_deposit(recipient, order_id),
            vc.judge_deposit(judge, order_id),
        )
        await cft.wait_for_block()

        await asyncio.gather(
            cft.assert_tx_success(api, rcpt_resp["id"]),
            cft.assert_tx_success(api, judge_resp["id"]),
        )

        rcpt_status, judge_status = await asyncio.gather(
            vc.get_order_recipient_deposit_status(order_id),
            vc.get_order_judge_deposit_status(order_id),
        )

        assert rcpt_status is True
        assert judge_status is True

        return vc, order_id

    @pytest.fixture
    async def new_ctrt_ten_mins_order_deposited(
        self,
        new_ctrt_ten_mins_order: Tuple[pv.VEscrowCtrt, str],
        recipient: pv.Account,
        judge: pv.Account,
    ) -> Tuple[pv.VEscrowCtrt, str]:
        """
        new_ctrt_ten_mins_order_deposited is the fixture that registers a new V Escrow Contract where
        - the payer duration & judge duration are all 10 mins
        - an order is created.
        - payer, recipient, & judge have all deposited into it.

        Args:
            new_ctrt_ten_mins_order (Tuple[pv.VEscrowCtrt, str]):
                The V Escrow contract instance where the order is created.
            recipient (pv.Account): The account of the contract recipient.
            judge (pv.Account): The account of the contract judge.

        Returns:
            Tuple[pv.VEscrowCtrt, str]: The VEscrowCtrt instance and the order_id
        """
        vc, order_id = new_ctrt_ten_mins_order
        return await self._deposit_to_order(vc, order_id, recipient, judge)

    @pytest.fixture
    async def new_ctrt_five_secs_order_deposited(
        self,
        new_ctrt_five_secs: pv.VEscrowCtrt,
        payer: pv.Account,
        recipient: pv.Account,
        judge: pv.Account,
    ) -> Tuple[pv.VEscrowCtrt, str]:
        """
        new_ctrt_five_secs_order is the fixture that registers
        a new V Escrow Contract where the payer duration & judge duration
        are all 5 seconds with an order created.

        Args:
            new_ctrt_five_secs (pv.VEscrowCtrt): The V Escrow contract instance.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.
            judge (pv.Account): The account of the contract judge.

        Returns:
            Tuple[pv.VEscrowCtrt, str]: The VEscrowCtrt instance and the order_id
        """
        vc = new_ctrt_five_secs
        vc, order_id = await self._create_order(vc, payer, recipient)
        return await self._deposit_to_order(vc, order_id, recipient, judge)

    @pytest.fixture
    async def new_ctrt_quick_expire_order_deposited(
        self,
        new_ctrt_five_secs: pv.VEscrowCtrt,
        payer: pv.Account,
        recipient: pv.Account,
        judge: pv.Account,
    ) -> Tuple[pv.VEscrowCtrt, str]:
        """
        new_ctrt_five_secs_order is the fixture that registers
        a new V Escrow Contract where the payer duration & judge duration
        are all 5 seconds with an order which is expiring SOON created.

        Args:
            new_ctrt_five_secs (pv.VEscrowCtrt): The V Escrow contract instance.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.
            judge (pv.Account): The account of the contract judge.

        Returns:
            Tuple[pv.VEscrowCtrt, str]: The VEscrowCtrt instance and the order_id
        """
        vc = new_ctrt_five_secs
        five_secs_later = int(time.time()) + 5
        vc, order_id = await self._create_order(vc, payer, recipient, five_secs_later)
        return await self._deposit_to_order(vc, order_id, recipient, judge)

    @pytest.fixture
    async def new_ctrt_ten_mins_work_submitted(
        self,
        new_ctrt_ten_mins_order_deposited: Tuple[pv.VEscrowCtrt, str],
        recipient: pv.Account,
    ) -> Tuple[pv.VEscrowCtrt, str]:
        """
        new_ctrt_ten_mins_work_submitted is the fixture that registers a new V Escrow Contract where
        - the payer duration & judge duration are all 10 mins
        - an order is created.
        - payer, recipient, & judge have all deposited into it.
        - recipient has submitted the work.

        Args:
            new_ctrt_ten_mins_order_deposited (Tuple[pv.VEscrowCtrt, str]): The V Escrow contract instance
                where the payer duration & judge duration are all 10 mins and an order has been created.
                Payer, recipient, and judge have all deposited into it.
            recipient (pv.Account): The account of the contract recipient.

        Returns:
            Tuple[pv.VEscrowCtrt, str]: The VEscrowCtrt instance and the order_id
        """
        vc, order_id = new_ctrt_ten_mins_order_deposited
        api = recipient.api

        resp = await vc.submit_work(recipient, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        return vc, order_id

    async def test_register(
        self,
        new_sys_ctrt: pv.SysCtrt,
        new_ctrt_ten_mins: pv.VEscrowCtrt,
        maker: pv.Account,
    ) -> pv.VEscrowCtrt:
        """
        test_register tests the method register.

        Args:
            new_sys_ctrt (pv.SysCtrt): The system contract instance.
            new_ctrt_ten_mins (pv.VEscrowCtrt): The V Escrow contract instance.
            maker (pv.Account): The account of the contract maker.

        Returns:
            pv.VEscrowCtrt: The VEscrowCtrt instance.
        """

        sc = new_sys_ctrt
        vc = new_ctrt_ten_mins

        assert (await vc.maker).data == maker.addr.b58_str
        assert (await vc.judge).data == maker.addr.b58_str

        tok_id = await vc.tok_id
        assert tok_id.data == sc.tok_id

        ten_mins = 10 * 60
        duration = await vc.duration
        assert duration.unix_ts == ten_mins

        judge_duration = await vc.judge_duration
        assert judge_duration.unix_ts == ten_mins

        assert (await vc.unit) == (await sc.unit)

    async def test_supersede(
        self,
        new_ctrt_ten_mins: pv.VEscrowCtrt,
        acnt0: pv.Account,
        acnt1: pv.Account,
    ) -> pv.VEscrowCtrt:
        """
        test_supersede tests the method supersede

        Args:
            new_ctrt_ten_mins (pv.VEscrowCtrt): The V Escrow contract instance.
            acnt0 (pv.Account): The account of nonce 0.
            acnt1 (pv.Account): The account of nonce 1.

        Returns:
            pv.VEscrowCtrt: The VEscrowCtrt instance.
        """

        vc = new_ctrt_ten_mins
        api = acnt0.api

        judge = await vc.judge
        assert judge.data == acnt0.addr.b58_str

        resp = await vc.supersede(acnt0, acnt1.addr.b58_str)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        judge = await vc.judge
        assert judge.data == acnt1.addr.b58_str

    async def test_create(
        self,
        new_ctrt_ten_mins: pv.VEscrowCtrt,
        judge: pv.Account,
        payer: pv.Account,
        recipient: pv.Account,
    ) -> None:
        """
        test_create tests the method create.

        Args:
            new_ctrt_ten_mins (pv.VEscrowCtrt): The V Escrow contract instance.
            maker (pv.Account): The account of the contract maker.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.
        """

        vc = new_ctrt_ten_mins
        api = judge.api
        a_day_later = int(time.time()) + 60 * 60 * 24

        resp = await vc.create(
            by=payer,
            recipient=recipient.addr.b58_str,
            amount=self.ORDER_AMOUNT,
            rcpt_deposit_amount=self.RCPT_DEPOSIT_AMOUNT,
            judge_deposit_amount=self.JUDGE_DEPOSIT_AMOUNT,
            order_fee=self.ORDER_FEE,
            refund_amount=self.REFUND_AMOUNT,
            expire_at=a_day_later,
        )
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        order_id = resp["id"]

        assert (await vc.get_order_payer(order_id)).data == payer.addr.b58_str
        assert (await vc.get_order_recipient(order_id)).data == recipient.addr.b58_str
        assert (await vc.get_order_amount(order_id)).amount == self.ORDER_AMOUNT
        assert (
            await vc.get_order_recipient_deposit(order_id)
        ).amount == self.RCPT_DEPOSIT_AMOUNT
        assert (
            await vc.get_order_judge_deposit(order_id)
        ).amount == self.JUDGE_DEPOSIT_AMOUNT
        assert (await vc.get_order_fee(order_id)).amount == self.ORDER_FEE
        assert (
            await vc.get_order_recipient_amount(order_id)
        ).amount == self.ORDER_AMOUNT - self.ORDER_FEE
        assert (await vc.get_order_refund(order_id)).amount == self.REFUND_AMOUNT

        total_in_order = (
            self.ORDER_AMOUNT + self.RCPT_DEPOSIT_AMOUNT + self.JUDGE_DEPOSIT_AMOUNT
        )
        assert (
            await vc.get_order_recipient_refund(order_id)
        ).amount == total_in_order - self.REFUND_AMOUNT
        assert (await vc.get_order_expiration_time(order_id)).unix_ts == a_day_later
        assert (await vc.get_order_status(order_id)) is True
        assert (await vc.get_order_recipient_deposit_status(order_id)) is False
        assert (await vc.get_order_judge_deposit_status(order_id)) is False
        assert (await vc.get_order_submit_status(order_id)) is False
        assert (await vc.get_order_judge_status(order_id)) is False
        assert (await vc.get_order_recipient_locked_amount(order_id)).amount == 0
        assert (await vc.get_order_judge_locked_amount(order_id)).amount == 0

    async def test_recipient_deposit(
        self,
        new_ctrt_ten_mins_order: Tuple[pv.VEscrowCtrt, str],
        recipient: pv.Account,
    ) -> None:
        """
        test_recipient_deposit tests the method recipient_deposit.

        Args:
            new_ctrt_ten_mins_order (Tuple[pv.VEscrowCtrt, str]): The V Escrow contract instance
                where the payer duration & judge duration are all 10 mins and an order has been created.
            recipient (pv.Account): The account of the contract recipient.
        """
        vc, order_id = new_ctrt_ten_mins_order
        api = recipient.api

        assert (await vc.get_order_recipient_deposit_status(order_id)) is False
        assert (await vc.get_order_recipient_locked_amount(order_id)).amount == 0

        resp = await vc.recipient_deposit(recipient, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_recipient_deposit_status(order_id)) is True
        assert (
            await vc.get_order_recipient_locked_amount(order_id)
        ).amount == self.RCPT_DEPOSIT_AMOUNT

    async def test_judge_deposit(
        self,
        new_ctrt_ten_mins_order: Tuple[pv.VEscrowCtrt, str],
        judge: pv.Account,
    ) -> None:
        """
        test_judge_deposit tests the method judge_deposit.

        Args:
            new_ctrt_ten_mins_order (Tuple[pv.VEscrowCtrt, str]): The V Escrow contract instance
                where the payer duration & judge duration are all 10 mins and an order has been created.
            judge (pv.Account): The account of the contract judge.
        """
        vc, order_id = new_ctrt_ten_mins_order
        api = judge.api

        assert (await vc.get_order_judge_deposit_status(order_id)) is False
        assert (await vc.get_order_judge_locked_amount(order_id)).amount == 0

        resp = await vc.judge_deposit(judge, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_judge_deposit_status(order_id)) is True
        assert (
            await vc.get_order_judge_locked_amount(order_id)
        ).amount == self.JUDGE_DEPOSIT_AMOUNT

    async def test_payer_cancel(
        self,
        new_ctrt_ten_mins_order: Tuple[pv.VEscrowCtrt, str],
        payer: pv.Account,
    ) -> None:
        """
        test_payer_cancel tests the method payer_cancel.

        Args:
            new_ctrt_ten_mins_order (Tuple[pv.VEscrowCtrt, str]): The V Escrow contract instance
                where the payer duration & judge duration are all 10 mins and an order has been created.
            payer (pv.Account): The account of the contract payer.
        """

        vc, order_id = new_ctrt_ten_mins_order
        api = payer.api

        assert (await vc.get_order_status(order_id)) is True

        resp = await vc.payer_cancel(payer, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_status(order_id)) is False

    async def test_recipient_cancel(
        self,
        new_ctrt_ten_mins_order: Tuple[pv.VEscrowCtrt, str],
        recipient: pv.Account,
    ) -> None:
        """
        test_recipient_cancel tests the method recipient_cancel.

        Args:
            new_ctrt_ten_mins_order (Tuple[pv.VEscrowCtrt, str]): The V Escrow contract instance
                where the payer duration & judge duration are all 10 mins and an order has been created.
            recipient (pv.Account): The account of the contract recipient.
        """

        vc, order_id = new_ctrt_ten_mins_order
        api = recipient.api

        assert (await vc.get_order_status(order_id)) is True

        resp = await vc.recipient_cancel(recipient, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_status(order_id)) is False

    async def test_judge_cancel(
        self,
        new_ctrt_ten_mins_order: Tuple[pv.VEscrowCtrt, str],
        judge: pv.Account,
    ) -> None:
        """
        test_judge_cancel tests the method judge_cancel.

        Args:
            new_ctrt_ten_mins_order (Tuple[pv.VEscrowCtrt, str]): The V Escrow contract instance
                where the payer duration & judge duration are all 10 mins and an order has been created.
            judge (pv.Account): The account of the contract judge.
        """

        vc, order_id = new_ctrt_ten_mins_order
        api = judge.api

        assert (await vc.get_order_status(order_id)) is True

        resp = await vc.judge_cancel(judge, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_status(order_id)) is False

    async def test_submit_work(
        self,
        new_ctrt_ten_mins_order_deposited: Tuple[pv.VEscrowCtrt, str],
        recipient: pv.Account,
    ) -> None:
        """
        test_submit_work tests the method submit_work.

        Args:
            new_ctrt_ten_mins_order_deposited (Tuple[pv.VEscrowCtrt, str]): The V Escrow contract instance
                where the payer duration & judge duration are all 10 mins and an order has been created.
                Payer, recipient, and judge have all deposited into it.
            recipient (pv.Account): The account of the contract recipient.
        """

        vc, order_id = new_ctrt_ten_mins_order_deposited
        api = recipient.api

        assert (await vc.get_order_submit_status(order_id)) is False

        resp = await vc.submit_work(recipient, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_submit_status(order_id)) is True

    async def test_approve_work(
        self,
        new_ctrt_ten_mins_work_submitted: Tuple[pv.VEscrowCtrt, str],
        payer: pv.Account,
        recipient: pv.Account,
        judge: pv.Account,
    ) -> None:
        """
        test_approve_work tests the method approve_work.

        Args:
            new_ctrt_ten_mins_work_submitted (Tuple[pv.VEscrowCtrt, str]):
                The V Escrow contract instance where the work has been submitted by the recipient.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.
            judge (pv.Account): The account of the contract judge.
        """
        vc, order_id = new_ctrt_ten_mins_work_submitted
        api = payer.api

        rcpt_bal_old, judge_bal_old = await asyncio.gather(
            vc.get_ctrt_bal(recipient.addr.b58_str), vc.get_ctrt_bal(judge.addr.b58_str)
        )

        assert (await vc.get_order_status(order_id)) is True

        resp = await vc.approve_work(payer, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_status(order_id)) is False

        rcpt_amt, fee, rcpt_dep, judge_dep, rcpt_bal, judge_bal = await asyncio.gather(
            vc.get_order_recipient_amount(order_id),
            vc.get_order_fee(order_id),
            vc.get_order_recipient_deposit(order_id),
            vc.get_order_judge_deposit(order_id),
            vc.get_ctrt_bal(recipient.addr.b58_str),
            vc.get_ctrt_bal(judge.addr.b58_str),
        )

        assert (
            rcpt_bal.amount - rcpt_bal_old.amount == rcpt_amt.amount + rcpt_dep.amount
        )
        assert judge_bal.amount - judge_bal_old.amount == fee.amount + judge_dep.amount

    async def test_apply_to_judge_and_do_judge(
        self,
        new_ctrt_ten_mins_work_submitted: Tuple[pv.VEscrowCtrt, str],
        payer: pv.Account,
        recipient: pv.Account,
        judge: pv.Account,
    ) -> None:
        """
        test_approve_work tests the method
        - apply_to_judge
        - do_judge

        Args:
            new_ctrt_ten_mins_work_submitted (Tuple[pv.VEscrowCtrt, str]):
                The V Escrow contract instance where the work has been submitted by the recipient.
            payer (pv.Account): The account of the contract payer.
            recipient (pv.Account): The account of the contract recipient.
            judge (pv.Account): The account of the contract judge.
        """
        vc, order_id = new_ctrt_ten_mins_work_submitted
        api = payer.api

        payer_bal_old, rcpt_bal_old, judge_bal_old = await asyncio.gather(
            vc.get_ctrt_bal(payer.addr.b58_str),
            vc.get_ctrt_bal(recipient.addr.b58_str),
            vc.get_ctrt_bal(judge.addr.b58_str),
        )
        assert (await vc.get_order_status(order_id)) is True

        resp = await vc.apply_to_judge(payer, order_id)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        # The judge is dividing the amount that
        # == payer_deposit + recipient_deposit - fee
        # In this case, the amount is 8
        to_payer = 3
        to_rcpt = 5

        resp = await vc.do_judge(judge, order_id, to_payer, to_rcpt)
        await cft.wait_for_block()
        await cft.assert_tx_success(api, resp["id"])

        assert (await vc.get_order_status(order_id)) is False

        fee, judge_dep, payer_bal, rcpt_bal, judge_bal = await asyncio.gather(
            vc.get_order_fee(order_id),
            vc.get_order_judge_deposit(order_id),
            vc.get_ctrt_bal(payer.addr.b58_str),
            vc.get_ctrt_bal(recipient.addr.b58_str),
            vc.get_ctrt_bal(judge.addr.b58_str),
        )

        assert payer_bal.amount - payer_bal_old.amount == to_payer
        assert rcpt_bal.amount - rcpt_bal_old.amount == to_rcpt
        assert judge_bal.amount - judge_bal_old.amount == fee.amount + judge_dep.amount
